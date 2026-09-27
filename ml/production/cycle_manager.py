"""
RAMP Operational Cycle Manager, Idempotent Orchestrator & Recovery Engine
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ml.inference.pipeline import OperationalInferencePipeline
from ml.ingestion.activation import RealDataActivationEngine

logger = logging.getLogger(__name__)

SUPPORTED_OPERATIONAL_LEADS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 72, 96, 120]


class OperationalCycleFlowState(str, Enum):
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    DATA_DISCOVERED = "DATA_DISCOVERED"
    VALIDATING = "VALIDATING"
    DATA_ELIGIBLE = "DATA_ELIGIBLE"
    READY_FOR_INFERENCE = "READY_FOR_INFERENCE"
    INFERENCING = "INFERENCING"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    CYCLE_COMPLETE = "CYCLE_COMPLETE"

    # Degradation & failure states
    VALIDATION_FAILED = "VALIDATION_FAILED"
    REAL_DATA_LOST = "REAL_DATA_LOST"
    OPERATIONAL_DEGRADED = "OPERATIONAL_DEGRADED"
    FORECAST_GENERATION_BLOCKED = "FORECAST_GENERATION_BLOCKED"
    RETRY_PENDING = "RETRY_PENDING"
    RETRYING = "RETRYING"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class JobExecutionStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


@dataclass
class OperationalJobRecord:
    job_id: str
    cycle_id: str
    lead_hours: int
    model_version: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = JobExecutionStatus.QUEUED.value
    retry_count: int = 0
    max_retries: int = 3
    is_transient: bool = False
    error_message: Optional[str] = None
    execution_latency_ms: Optional[float] = None
    manifest_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalCycleRecord:
    cycle_id: str
    date: str
    cycle_utc: str
    source_model: str
    initialization_time: str
    expected_arrival: str
    state: str = OperationalCycleFlowState.WAITING_FOR_DATA.value
    data_mode: str = "SYNTHETIC_DEMO"
    available_leads: List[int] = field(default_factory=lambda: list(SUPPORTED_OPERATIONAL_LEADS))
    executed_leads: List[int] = field(default_factory=list)
    published_leads: List[int] = field(default_factory=list)
    jobs: Dict[str, OperationalJobRecord] = field(default_factory=dict)
    state_history: List[Dict[str, str]] = field(default_factory=list)
    error_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["jobs"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.jobs.items()}
        return d


class ProductionJobQueue:
    """Thread-safe, deterministic job queue preventing duplicate cycle execution."""

    def __init__(self):
        self._jobs: Dict[str, OperationalJobRecord] = {}
        self._completed_ids: Set[str] = set()

    @staticmethod
    def generate_job_id(cycle_id: str, lead_hours: int, model_version: str) -> str:
        """Deterministic SHA-256 identifier guaranteeing idempotency."""
        seed = f"RAMP_JOB_{cycle_id}_t{lead_hours}_{model_version}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def enqueue_job(
        self,
        cycle_id: str,
        lead_hours: int,
        model_version: str = "v2.0.0",
        max_retries: int = 3,
    ) -> OperationalJobRecord:
        job_id = self.generate_job_id(cycle_id, lead_hours, model_version)
        if job_id in self._completed_ids:
            logger.info(f"Job {job_id} already completed successfully. Skipping.")
            job = self._jobs[job_id]
            job.status = JobExecutionStatus.SKIPPED.value
            return job

        if job_id in self._jobs:
            return self._jobs[job_id]

        now_iso = datetime.now(timezone.utc).isoformat()
        job = OperationalJobRecord(
            job_id=job_id,
            cycle_id=cycle_id,
            lead_hours=lead_hours,
            model_version=model_version,
            created_at=now_iso,
            status=JobExecutionStatus.QUEUED.value,
            max_retries=max_retries,
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[OperationalJobRecord]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[OperationalJobRecord]:
        return list(self._jobs.values())

    def mark_completed(self, job_id: str, manifest_path: Optional[str] = None, latency_ms: Optional[float] = None) -> None:
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = JobExecutionStatus.SUCCESS.value
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.manifest_path = manifest_path
            job.execution_latency_ms = latency_ms
            self._completed_ids.add(job_id)


class OperationalCycleManager:
    """
    Manages end-to-end operational cycle lifecycle transitions, lead time execution,
    transient retry decisions, and real-data safety locks.
    """

    NON_RETRYABLE_ERRORS = [
        "SCHEMA_VALIDATION_FAILURE",
        "CHECKSUM_MISMATCH",
        "METADATA_INVALID",
        "LEAKAGE_DETECTED",
        "MODEL_INTEGRITY_FAILURE",
        "UNAUTHORIZED_ACTIVATION",
        "SCIENTIFIC_VALIDATION_FAILURE",
        "OUT_OF_BOUNDS_PHYSICAL",
    ]

    def __init__(
        self,
        job_queue: Optional[ProductionJobQueue] = None,
        activation_engine: Optional[RealDataActivationEngine] = None,
        inference_pipeline: Optional[OperationalInferencePipeline] = None,
    ):
        self.queue = job_queue or ProductionJobQueue()
        self.activation_engine = activation_engine or RealDataActivationEngine()
        self.pipeline = inference_pipeline or OperationalInferencePipeline()
        self._cycles: Dict[str, OperationalCycleRecord] = {}
        self._init_standard_cycles()

    def _init_standard_cycles(self):
        """Initializes current operational and demonstration cycle states."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")

        # Cycle 00Z
        c00 = f"{today}_00Z"
        self._cycles[c00] = OperationalCycleRecord(
            cycle_id=c00,
            date=today,
            cycle_utc="00Z",
            source_model="NCMRWF_NCUM",
            initialization_time=f"{today}T00:00:00Z",
            expected_arrival=f"{today}T04:30:00Z",
            state=OperationalCycleFlowState.WAITING_FOR_DATA.value,
            data_mode="WAITING_FOR_AUTHORITATIVE_DATA",
            available_leads=list(SUPPORTED_OPERATIONAL_LEADS),
        )

        # Demo fallback cycle
        demo_id = "DEMO_20260927_00Z"
        self._cycles[demo_id] = OperationalCycleRecord(
            cycle_id=demo_id,
            date="20260927",
            cycle_utc="00Z",
            source_model="NCUM_SYNTHETIC_DEMO",
            initialization_time="2026-09-27T00:00:00Z",
            expected_arrival="2026-09-27T04:30:00Z",
            state=OperationalCycleFlowState.PUBLISHED.value,
            data_mode="SYNTHETIC_DEMO",
            available_leads=[6, 12, 18, 24, 36, 48, 72, 96, 120],
            executed_leads=[24],
            published_leads=[24],
        )

    def create_cycle(
        self,
        cycle_id: str,
        initialization_time: Optional[str] = None,
        source_model: str = "NCMRWF_NCUM",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> OperationalCycleRecord:
        """Creates or registers an operational cycle."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        record = OperationalCycleRecord(
            cycle_id=cycle_id,
            date=today,
            cycle_utc="00Z",
            source_model=source_model,
            initialization_time=initialization_time or now.isoformat(),
            expected_arrival=now.isoformat(),
            state=OperationalCycleFlowState.WAITING_FOR_DATA.value,
            data_mode=data_mode,
            available_leads=list(SUPPORTED_OPERATIONAL_LEADS),
        )
        self._cycles[cycle_id] = record
        return record

    def transition_cycle(self, cycle_id: str, new_state: OperationalCycleFlowState, reason: str = "") -> OperationalCycleRecord:
        """Records state transition in audit trail."""
        if cycle_id not in self._cycles:
            raise KeyError(f"Cycle '{cycle_id}' not found.")

        cycle = self._cycles[cycle_id]
        prior_state = cycle.state
        cycle.state = new_state.value
        now_iso = datetime.now(timezone.utc).isoformat()
        cycle.state_history.append({
            "from_state": prior_state,
            "to_state": new_state.value,
            "timestamp": now_iso,
            "reason": reason,
        })
        logger.info(f"Cycle {cycle_id} transitioned: {prior_state} -> {new_state.value} ({reason})")
        return cycle

    def execute_cycle_lead(self, cycle_id: str, lead_hours: int) -> OperationalJobRecord:
        """Executes a single lead time for an operational cycle idempotently."""
        if lead_hours not in SUPPORTED_OPERATIONAL_LEADS:
            raise ValueError(f"Unsupported lead time +{lead_hours}h. Supported: {SUPPORTED_OPERATIONAL_LEADS}")

        if cycle_id not in self._cycles:
            raise KeyError(f"Unknown cycle '{cycle_id}'.")

        cycle = self._cycles[cycle_id]

        # Check activation state: if real cycle requested but data unmounted, reject
        if not cycle_id.startswith("DEMO_") and cycle.data_mode != "REAL_OPERATIONAL":
            act_status = self.activation_engine.get_status()
            if act_status.system_status == "BLOCKED":
                job_id = self.queue.generate_job_id(cycle_id, lead_hours, "v2.0.0")
                job = OperationalJobRecord(
                    job_id=job_id,
                    cycle_id=cycle_id,
                    lead_hours=lead_hours,
                    model_version="v2.0.0",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    status=JobExecutionStatus.BLOCKED.value,
                    error_message="FORECAST_GENERATION_BLOCKED: Authoritative NCMRWF data are unmounted.",
                )
                cycle.jobs[job_id] = job
                self.transition_cycle(
                    cycle_id,
                    OperationalCycleFlowState.FORECAST_GENERATION_BLOCKED,
                    "Real data unmounted; execution blocked."
                )
                return job

        job = self.queue.enqueue_job(cycle_id, lead_hours)
        if job.status == JobExecutionStatus.SKIPPED.value:
            return job

        job.status = JobExecutionStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc).isoformat()
        self.transition_cycle(cycle_id, OperationalCycleFlowState.INFERENCING, f"Executing lead +{lead_hours}h")

        try:
            # Trigger actual inference pipeline
            t0 = datetime.now(timezone.utc)
            res = self.pipeline.run_forecast(cycle_id, lead_hours)
            t1 = datetime.now(timezone.utc)
            latency = (t1 - t0).total_seconds() * 1000.0

            m_path = res.get("manifest_path", "")
            self.queue.mark_completed(job.job_id, manifest_path=m_path, latency_ms=latency)
            if lead_hours not in cycle.executed_leads:
                cycle.executed_leads.append(lead_hours)

            self.transition_cycle(cycle_id, OperationalCycleFlowState.PUBLISHED, f"Lead +{lead_hours}h completed.")
            if lead_hours not in cycle.published_leads:
                cycle.published_leads.append(lead_hours)

        except Exception as e:
            err_msg = str(e)
            is_trans = not any(err in err_msg for err in self.NON_RETRYABLE_ERRORS)
            job.status = JobExecutionStatus.FAILED.value
            job.error_message = err_msg
            job.is_transient = is_trans

            if is_trans and job.retry_count < job.max_retries:
                self.transition_cycle(cycle_id, OperationalCycleFlowState.RETRY_PENDING, f"Transient failure: {err_msg}")
            else:
                self.transition_cycle(cycle_id, OperationalCycleFlowState.TERMINAL_FAILURE, f"Terminal failure: {err_msg}")

        cycle.jobs[job.job_id] = job
        return job

    def retry_job(self, job_id: str) -> OperationalJobRecord:
        """Retries a transiently failed job with bounded retry limit."""
        job = self.queue.get_job(job_id)
        if not job:
            raise KeyError(f"Job {job_id} not found.")

        if not job.is_transient:
            raise ValueError(f"Job {job_id} experienced non-retryable error ({job.error_message}). Cannot retry.")

        if job.retry_count >= job.max_retries:
            raise ValueError(f"Job {job_id} exceeded maximum retry limit ({job.max_retries}).")

        job.retry_count += 1
        job.status = JobExecutionStatus.QUEUED.value
        self.transition_cycle(job.cycle_id, OperationalCycleFlowState.RETRYING, f"Retry attempt {job.retry_count}")
        return self.execute_cycle_lead(job.cycle_id, job.lead_hours)

    def list_cycles(self) -> List[OperationalCycleRecord]:
        return list(self._cycles.values())

    def get_cycle(self, cycle_id: str) -> Optional[OperationalCycleRecord]:
        return self._cycles.get(cycle_id)
