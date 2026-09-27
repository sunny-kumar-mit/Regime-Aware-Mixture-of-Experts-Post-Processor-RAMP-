"""
Phase 15 — Forecast Scheduler & Job Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

The scheduler monitors for new NWP cycles at configurable intervals.
It is idempotent: running the same (provider, model, cycle, lead, model_version)
combination twice will not rerun inference — it returns the cached result.

INTEGRITY GUARANTEE:
  - Scheduler does NOT fabricate real operational cycles.
  - It delegates cycle resolution to ForecastCycleResolver.
  - SYNTHETIC_DEMO cycles are clearly labelled in every job record.
  - No silent fallback to real data; data_mode is always explicit.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ml.inference.input_resolver import ForecastCycleResolver
from ml.inference.model_resolver import ModelResolver
from ml.inference.pipeline import OperationalInferencePipeline
from ml.operations.state import OperationalState, OperationalStateMachine

logger = logging.getLogger(__name__)

# ── Scheduler Defaults ──────────────────────────────────────────────────────
DEFAULT_POLL_INTERVAL_S = 300  # 5 min — check for new cycles every 5 minutes
DEFAULT_LEAD_HOURS = [24, 48, 72, 96, 120]  # Standard operational leads


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # idempotent: already completed this cycle+lead


@dataclass
class ForecastJob:
    """Record of a single (cycle, lead) inference execution."""

    job_id: str
    cycle_id: str
    lead_hours: int
    model_version: str
    provider_id: str
    data_mode: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    forecast_run_id: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    validation_gates_passed: int = 0
    skip_reason: Optional[str] = None

    @classmethod
    def make_job_id(cls, cycle_id: str, lead_hours: int, model_version: str) -> str:
        raw = f"{cycle_id}|{lead_hours}|{model_version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class ForecastScheduler:
    """
    Automated cycle-aware forecast scheduler.

    Runs as a background thread, polling for new NWP cycles at
    `poll_interval_s` second intervals. For each discovered cycle + lead
    combination that has not been completed, it submits a ForecastJob.

    Idempotency: A job (cycle_id, lead_hours, model_version) is only run
    once; re-discovery of the same cycle is a no-op (SKIPPED).
    """

    def __init__(
        self,
        state_machine: OperationalStateMachine,
        poll_interval_s: int = DEFAULT_POLL_INTERVAL_S,
        lead_hours: Optional[List[int]] = None,
    ):
        self._state = state_machine
        self._poll_interval = poll_interval_s
        self._lead_hours = lead_hours or DEFAULT_LEAD_HOURS

        self._cycle_resolver = ForecastCycleResolver()
        self._model_resolver = ModelResolver()
        self._pipeline = OperationalInferencePipeline(
            model_resolver=self._model_resolver,
            cycle_resolver=self._cycle_resolver,
        )

        self._jobs: Dict[str, ForecastJob] = {}       # job_id → job
        self._completed: set = set()                   # job_id set for idempotency
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._enabled = False
        self._poll_count = 0
        self._last_poll_at: Optional[str] = None
        self._scheduler_start_at: Optional[str] = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._enabled:
            logger.warning("Scheduler already running.")
            return
        self._enabled = True
        self._stop_event.clear()
        self._scheduler_start_at = datetime.now(timezone.utc).isoformat()
        self._thread = threading.Thread(
            target=self._run_loop, name="ForecastScheduler", daemon=True
        )
        self._thread.start()
        logger.info(f"ForecastScheduler started (poll={self._poll_interval}s, leads={self._lead_hours}h)")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._enabled = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("ForecastScheduler stopped.")

    def is_running(self) -> bool:
        return self._enabled and (self._thread is not None) and self._thread.is_alive()

    # ── Scheduler Loop ───────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_cycle()
            except Exception as exc:
                logger.error(f"Scheduler poll error: {exc}", exc_info=True)
            self._stop_event.wait(self._poll_interval)

    def _poll_cycle(self) -> None:
        self._poll_count += 1
        self._last_poll_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Scheduler poll #{self._poll_count} at {self._last_poll_at}")

        # Transition to DATA_RECEIVED phase
        current = self._state.current_state
        if current in (OperationalState.WAITING_FOR_DATA, OperationalState.CYCLE_COMPLETE):
            cycles = self._cycle_resolver.list_available_cycles()
            if not cycles:
                return
            self._state.transition(
                OperationalState.DATA_RECEIVED,
                reason=f"Discovered {len(cycles)} cycle(s)",
                triggered_by="SCHEDULER",
            )
            self._state.transition(
                OperationalState.VALIDATING,
                reason="Pre-inference validation starting",
                triggered_by="SCHEDULER",
            )
            # Submit jobs for each cycle × lead combination
            all_ok = True
            for cycle in cycles:
                for lead in self._lead_hours:
                    if lead not in cycle.available_leads:
                        continue
                    try:
                        model_info = self._model_resolver.resolve_moe()
                    except Exception:
                        model_info = None
                    mv = model_info.version if model_info else "v2.0.0"
                    job = self._submit_job(cycle.cycle_id, lead, mv, cycle.provider_id, cycle.data_mode)
                    if job.status == JobStatus.FAILED:
                        all_ok = False

            if all_ok:
                self._state.transition(
                    OperationalState.PUBLISHED,
                    reason="All jobs completed",
                    triggered_by="SCHEDULER",
                )
                self._state.transition(
                    OperationalState.CYCLE_COMPLETE,
                    reason="Scheduler cycle archived",
                    triggered_by="SCHEDULER",
                )
            else:
                self._state.transition(
                    OperationalState.VALIDATION_FAILED,
                    reason="One or more forecast jobs failed",
                    triggered_by="SCHEDULER",
                )

    # ── Job Management ───────────────────────────────────────────────────────

    def _submit_job(
        self,
        cycle_id: str,
        lead_hours: int,
        model_version: str,
        provider_id: str,
        data_mode: str,
    ) -> ForecastJob:
        job_id = ForecastJob.make_job_id(cycle_id, lead_hours, model_version)

        with self._lock:
            if job_id in self._completed:
                skip = ForecastJob(
                    job_id=job_id,
                    cycle_id=cycle_id,
                    lead_hours=lead_hours,
                    model_version=model_version,
                    provider_id=provider_id,
                    data_mode=data_mode,
                    status=JobStatus.SKIPPED,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    skip_reason="Idempotency: already completed",
                )
                return skip

            job = ForecastJob(
                job_id=job_id,
                cycle_id=cycle_id,
                lead_hours=lead_hours,
                model_version=model_version,
                provider_id=provider_id,
                data_mode=data_mode,
                status=JobStatus.PENDING,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._jobs[job_id] = job

        return self._execute_job(job)

    def submit_manual_job(self, cycle_id: str, lead_hours: int) -> ForecastJob:
        """Operator-triggered manual forecast job (bypasses poll schedule)."""
        try:
            model_info = self._model_resolver.resolve_moe()
            mv = model_info.version
        except Exception:
            mv = "v2.0.0"

        cycle = self._cycle_resolver.get_cycle(cycle_id)
        if cycle is None:
            raise ValueError(f"Unknown cycle_id: {cycle_id}")

        return self._submit_job(cycle_id, lead_hours, mv, cycle.provider_id, cycle.data_mode)

    def _execute_job(self, job: ForecastJob) -> ForecastJob:
        t0 = time.monotonic()
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Job {job.job_id}: {job.cycle_id}+{job.lead_hours}h RUNNING")

        try:
            result = self._pipeline.run_forecast(
                cycle_id=job.cycle_id,
                lead_time_hours=job.lead_hours,
                user_action="SCHEDULER",
            )
            if result.get("status") == "SUCCESS":
                job.status = JobStatus.SUCCESS
                job.forecast_run_id = result.get("forecast_run_id")
                job.validation_gates_passed = result.get("validation_gates_passed", 11)
            else:
                job.status = JobStatus.FAILED
                job.error_message = result.get("error", "Unknown inference error")
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            logger.error(f"Job {job.job_id} failed: {exc}", exc_info=True)

        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.duration_ms = (time.monotonic() - t0) * 1000.0

        with self._lock:
            if job.status == JobStatus.SUCCESS:
                self._completed.add(job.job_id)
            self._jobs[job.job_id] = job

        logger.info(
            f"Job {job.job_id}: {job.status.value} in {job.duration_ms:.0f}ms "
            f"(run={job.forecast_run_id})"
        )
        return job

    # ── Status API ───────────────────────────────────────────────────────────

    def get_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            j = self._jobs.get(job_id)
        return j.to_dict() if j else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._jobs)
            success = sum(1 for j in self._jobs.values() if j.status == JobStatus.SUCCESS)
            failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)
            running = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
            skipped = sum(1 for j in self._jobs.values() if j.status == JobStatus.SKIPPED)
        return {
            "scheduler_enabled": self._enabled,
            "is_running": self.is_running(),
            "poll_interval_s": self._poll_interval,
            "poll_count": self._poll_count,
            "last_poll_at": self._last_poll_at,
            "scheduler_start_at": self._scheduler_start_at,
            "lead_hours": self._lead_hours,
            "job_summary": {
                "total": total,
                "success": success,
                "failed": failed,
                "running": running,
                "skipped": skipped,
            },
        }
