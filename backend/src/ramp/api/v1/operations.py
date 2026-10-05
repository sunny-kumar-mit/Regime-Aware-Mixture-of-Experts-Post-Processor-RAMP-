"""
Phase 20 — Operations Control Center REST API & PostgreSQL Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Unified endpoints backed by PostgreSQL and OperationsEngine:
  1.  GET  /api/operations/status           — Full operations status snapshot
  2.  GET  /api/operations/overview         — Live overview metrics (state, alerts, drift, scheduler)
  3.  GET  /api/operations/state            — Current state machine state & history
  4.  POST /api/operations/state/transition — State machine transition (validated server-side)
  5.  GET  /api/operations/scheduler        — Scheduler status & config
  6.  GET  /api/operations/scheduler/status — Scheduler status alias
  7.  POST /api/operations/scheduler/start  — Start automated scheduler
  8.  POST /api/operations/scheduler/stop   — Stop automated scheduler
  9.  GET  /api/operations/jobs             — List recent forecast jobs
  10. GET  /api/operations/jobs/{job_id}    — Single job detail
  11. POST /api/operations/jobs             — Submit forecast job
  12. POST /api/operations/jobs/submit      — Submit forecast job (alias)
  13. GET  /api/operations/alerts           — Active & recent operational alerts
  14. POST /api/operations/alerts/{id}/acknowledge — Acknowledge alert
  15. POST /api/operations/alerts/{id}/resolve     — Resolve alert
  16. GET  /api/operations/drift            — Real drift measurements
  17. GET  /api/operations/readiness        — Dynamic 30-point readiness inspection
  18. GET  /api/operations/cycles           — Synoptic operational cycles (00Z & 12Z)
  19. GET  /api/operations/cycles/{cycle_id}— Single cycle detail & timeline
  20. POST /api/operations/cycles/{cycle_id}/retry — Retry cycle execution
  21. GET  /api/operations/health           — Compact health probe
  22. GET  /api/operations/gates            — 14-Gate Operational Cutover Engine
  23. GET  /api/operations/events           — Operational event audit timeline
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ramp.services.operations_engine import OperationsEngine, OperationalState
from ml.operations.alerts import BUILT_IN_RULES
from ml.operations.drift import DriftMonitor
from ml.operations.production import ProductionReadinessEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["Operations Control Center"])


def _engine() -> OperationsEngine:
    return OperationsEngine.get_instance()


# ── Request Models ────────────────────────────────────────────────────────────

class TransitionRequest(BaseModel):
    to_state: Optional[str] = Field(None, description="Target state name (e.g. WAITING_FOR_DATA)")
    event: Optional[str] = Field(None, description="Event name (e.g. DATA_RECEIVED)")
    reason: str = Field(default="Operator force-transition", description="Reason for transition")
    operator: str = Field(default="OPERATOR", description="Operator identifier")
    cycle_id: Optional[str] = Field(default=None, description="Optional cycle ID")


class JobSubmitRequest(BaseModel):
    cycle_id: str = Field(..., description="Forecast cycle ID (e.g. DEMO_20260927_00Z or 20261005_00Z)")
    lead_hours: int = Field(..., ge=6, le=240, description="Lead time in hours (6–240)")
    model_version: str = Field(default="v2.0.0", description="Model version")


class SchedulerConfigRequest(BaseModel):
    poll_interval_s: int = Field(default=300, ge=30, le=3600, description="Poll interval in seconds")
    lead_hours: Optional[List[int]] = Field(default=None, description="Lead times to schedule")


class AlertAckRequest(BaseModel):
    operator: str = Field(default="OPERATOR", description="Operator name")


class OpEmergencyStopRequest(BaseModel):
    actor: str = "OPERATOR"
    role: str = "OPERATOR"
    reason: str = "Operator emergency intervention"


class OpEmergencyRecoverRequest(BaseModel):
    actor: str = "SUPERVISOR"
    role: str = "SUPERVISOR"
    justification: str = "Supervisor operational clearance"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", summary="Full Operations Status Snapshot")
async def get_operations_status() -> Dict[str, Any]:
    """Returns a full live operations status snapshot backed by PostgreSQL."""
    st = _engine().get_full_operations_status()
    # Format scheduler sub-dict for backwards-compatibility with test suites
    sched = dict(st.get("scheduler", {}))
    sched.setdefault("scheduler_enabled", sched.get("is_running", False))
    st["scheduler"] = sched
    return st


@router.get("/overview", summary="Operations Overview Cards")
async def get_operations_overview() -> Dict[str, Any]:
    """Returns overview card metrics for dashboard display."""
    st = _engine().get_full_operations_status()
    return {
        "status": "SUCCESS",
        "system_state": st["state_machine"]["current_state"],
        "data_mode": st["data_mode"],
        "operational_gate": "OPEN" if st["gates"]["real_operational"] else "BLOCKED",
        "active_alerts": st["alerts"]["active"],
        "critical_alerts": st["alerts"]["critical"],
        "drift_level": st["drift"]["overall_level"],
        "scheduler_running": st["scheduler"]["is_running"],
        "timestamp": st["generated_at"],
    }


@router.get("/state", summary="State Machine State & Transition History")
async def get_state() -> Dict[str, Any]:
    """Returns current state, valid transitions, and transition history from PostgreSQL."""
    snap = _engine().get_state_snapshot()
    # Backwards compatible state_machine dictionary representation
    return {
        **snap,
        "current_state": snap["current_state"],
        "state_name": snap["current_state"],
        "transition_history": snap.get("transition_history", []),
        "valid_next_states": snap.get("valid_next_states", []),
    }


@router.post("/state/transition", summary="State Machine Transition")
async def post_state_transition(req: TransitionRequest) -> Dict[str, Any]:
    """
    Executes a deterministic state machine transition.
    Validates legality server-side; invalid transitions return 400.
    """
    target_state_str = req.to_state or req.event
    if not target_state_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'to_state' or 'event' must be provided.",
        )

    # Normalize state name
    try:
        target_state = OperationalState(target_state_str)
    except ValueError:
        # Check if mapped from event
        mapped = None
        for s in OperationalState:
            if s.value == target_state_str or f"TRANSITION_TO_{s.value}" == target_state_str:
                mapped = s
                break
        if not mapped:
            valid = [s.value for s in OperationalState]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state '{target_state_str}'. Valid states: {valid}",
            )
        target_state = mapped

    try:
        # If requested by operator override or forced
        if req.operator and req.operator.upper() in ["OPERATOR", "ADMIN", "SUPERVISOR"]:
            res = _engine().force_transition(
                to_state=target_state,
                reason=req.reason,
                operator=req.operator,
                cycle_id=req.cycle_id,
            )
        else:
            res = _engine().transition(
                to_state=target_state,
                event_name=req.event,
                reason=req.reason,
                operator=req.operator,
                cycle_id=req.cycle_id,
            )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"State transition failure: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/scheduler", summary="Scheduler Status & Configuration")
@router.get("/scheduler/status", summary="Scheduler Status Alias")
async def get_scheduler() -> Dict[str, Any]:
    """Returns scheduler running state, poll interval, and job summary from PostgreSQL."""
    sched = _engine().get_scheduler_status()
    # Backwards-compatibility fields for test suites
    sched.setdefault("scheduler_enabled", sched.get("is_running", False))
    return sched


@router.post("/scheduler/start", summary="Start Automated Forecast Scheduler")
async def start_scheduler(config: Optional[SchedulerConfigRequest] = None) -> Dict[str, Any]:
    """Starts the automated synoptic forecast scheduler background worker."""
    poll_s = config.poll_interval_s if config else None
    res = _engine().start_scheduler(poll_interval_s=poll_s)
    res.setdefault("scheduler_enabled", res.get("is_running", True))
    return res


@router.post("/scheduler/stop", summary="Stop Automated Forecast Scheduler")
async def stop_scheduler() -> Dict[str, Any]:
    """Gracefully stops the automated scheduler."""
    res = _engine().stop_scheduler()
    res.setdefault("scheduler_enabled", res.get("is_running", False))
    return res


@router.get("/jobs", summary="List Recent Forecast Jobs")
async def list_jobs(
    limit: int = 50,
    cycle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Returns execution jobs persisted in PostgreSQL."""
    jobs = _engine().list_jobs(limit=limit, cycle_id=cycle_id)
    sched = _engine().get_scheduler_status()
    return {
        "status": "SUCCESS",
        "jobs": jobs,
        "total_returned": len(jobs),
        "scheduler_running": sched.get("is_running", False),
        "job_summary": sched.get("job_summary", {}),
    }


@router.get("/jobs/{job_id}", summary="Single Forecast Job Detail")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Returns specific job detail by job_id."""
    jobs = _engine().list_jobs(limit=1000)
    for j in jobs:
        if j.get("job_id") == job_id:
            return j
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found")


@router.post("/jobs", summary="Submit Manual Forecast Job")
@router.post("/jobs/submit", summary="Submit Manual Forecast Job Alias")
async def submit_job(req: JobSubmitRequest) -> Dict[str, Any]:
    """
    Submits a forecast job with strict idempotency (cycle_id + lead_hours + model_version).
    Duplicate submissions are automatically SKIPPED.
    """
    try:
        res = _engine().submit_forecast_job(
            cycle_id=req.cycle_id,
            lead_hours=req.lead_hours,
            model_version=req.model_version,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Job submission error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/alerts", summary="Active & Historical Operational Alerts")
async def get_alerts(include_resolved: bool = False) -> Dict[str, Any]:
    """Returns alerts and rules evaluated against PostgreSQL and active pipeline metrics."""
    return _engine().get_alerts(include_resolved=include_resolved)


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge Alert")
async def acknowledge_alert(alert_id: str, req: Optional[AlertAckRequest] = None) -> Dict[str, Any]:
    """Marks an active alert as acknowledged in PostgreSQL."""
    op = req.operator if req else "OPERATOR"
    ok = _engine().acknowledge_alert(alert_id, operator=op)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found or already acknowledged.",
        )
    return {"success": True, "alert_id": alert_id, "acknowledged_by": op}


@router.post("/alerts/{alert_id}/resolve", summary="Resolve Alert")
async def resolve_alert(alert_id: str) -> Dict[str, Any]:
    """Marks an alert as resolved in PostgreSQL."""
    ok = _engine().resolve_alert(alert_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found or already resolved.",
        )
    return {"success": True, "alert_id": alert_id}


@router.get("/drift", summary="Latest Drift Report")
async def get_drift_report() -> Dict[str, Any]:
    """
    Returns statistical feature and prediction drift calculations.
    Truthfully reports INSUFFICIENT_DATA if minimum sample requirements are not met.
    """
    return _engine().compute_drift()


@router.get("/readiness", summary="30-Point Production Readiness Checklist")
async def get_readiness() -> Dict[str, Any]:
    """
    Evaluates the 30-point pre-launch readiness checklist across CAT-A through CAT-F.
    Score is calculated dynamically from live system and filesystem state.
    """
    return _engine().evaluate_readiness()


@router.get("/cycles", summary="List Synoptic Operational Cycles")
async def list_cycles(limit: int = 20) -> Dict[str, Any]:
    """Lists 00Z and 12Z synoptic operational cycles from PostgreSQL."""
    cycles = _engine().list_cycles(limit=limit)
    return {
        "status": "SUCCESS",
        "count": len(cycles),
        "cycles": cycles,
        "data": {"cycles": cycles},
    }


@router.get("/cycles/{cycle_id}", summary="Cycle Detail & Audit Timeline")
async def get_cycle(cycle_id: str) -> Dict[str, Any]:
    """Returns details and full event timeline for an operational cycle."""
    detail = _engine().get_cycle_detail(cycle_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle '{cycle_id}' not found.")
    return {
        "status": "SUCCESS",
        "cycle": detail,
        "data": detail,
    }


@router.post("/cycles/{cycle_id}/retry", summary="Retry Cycle Execution")
async def retry_cycle(cycle_id: str) -> Dict[str, Any]:
    """Requeues and executes pending lead times for a cycle."""
    detail = _engine().get_cycle_detail(cycle_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle '{cycle_id}' not found.")

    res = _engine().submit_forecast_job(cycle_id=cycle_id, lead_hours=24)
    return {
        "status": "SUCCESS",
        "message": f"Retry queued for cycle {cycle_id} (+24h).",
        "job": res.get("job"),
    }


@router.get("/health", summary="Compact Operations Health Probe")
async def get_health() -> Dict[str, Any]:
    """Lightweight health probe reporting operational status."""
    st = _engine().get_full_operations_status()
    db_health = _engine().db.check_health()
    is_up = db_health.get("connected", False)
    active_alerts = st.get("alerts", {}).get("active", 0)
    critical_alerts = st.get("alerts", {}).get("critical", 0)

    return {
        "status": "HEALTHY" if is_up and critical_alerts == 0 else "DEGRADED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_mode": st.get("data_mode", "SYNTHETIC_DEMO"),
        "state": st.get("state_machine", {}).get("current_state", "WAITING_FOR_DATA"),
        "scheduler_running": st.get("scheduler", {}).get("is_running", False),
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "disclaimer": st.get("banner", ""),
    }


@router.get("/gates", summary="14-Gate Operational Cutover Engine")
async def get_cutover_gates() -> Dict[str, Any]:
    from ml.operations.operational_state_service import OperationalStateService
    op_service = OperationalStateService.get_instance()
    gates = op_service.evaluate_14_cutover_gates()
    verdict = op_service.calculate_cutover_verdict()
    return {
        "status": "SUCCESS",
        "count": len(gates),
        "cutover_verdict": verdict,
        "gates": [g.to_dict() for g in gates],
        "data": {"gates": [g.to_dict() for g in gates], "verdict": verdict},
    }


@router.get("/events", summary="Operational Event Timeline")
async def get_operational_events(limit: int = 50) -> Dict[str, Any]:
    from ml.operations.operational_state_service import OperationalStateService
    op_service = OperationalStateService.get_instance()
    events = op_service.get_operational_events(limit=limit)
    return {
        "status": "SUCCESS",
        "count": len(events),
        "events": events,
        "data": {"events": events},
    }


@router.post("/emergency-stop", summary="Emergency Stop")
async def trigger_emergency_stop_op(req: OpEmergencyStopRequest):
    from ml.operations.operational_state_service import OperationalStateService
    op_service = OperationalStateService.get_instance()
    res = op_service.trigger_emergency_stop(actor=req.actor, reason=req.reason, role=req.role)
    return {"status": "SUCCESS", "emergency_status": res, "data": res}


@router.post("/emergency-recover", summary="Emergency Recovery")
async def recover_emergency_stop_op(req: OpEmergencyRecoverRequest):
    from ml.operations.operational_state_service import OperationalStateService
    op_service = OperationalStateService.get_instance()
    res = op_service.recover_emergency_stop(actor=req.actor, justification=req.justification, role=req.role)
    return {"status": "SUCCESS", "emergency_status": res, "data": res}
