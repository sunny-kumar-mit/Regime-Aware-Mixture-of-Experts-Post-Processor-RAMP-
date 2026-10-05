"""
Phase 20 Tests — Operational Control, Operational Cycles & Data Health
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Validates:
1. OperationsEngine initialization & DB state models.
2. Deterministic State Machine legal transitions and illegal transition rejection.
3. Transition audit logging to operation_events.
4. Synoptic 00Z / 12Z cycle generation, delay, freshness, and SLA calculations.
5. Cycle chronological events timeline persistence.
6. Scheduler background worker start/stop, status tracking, and single-instance safety.
7. Forecast job idempotency (duplicate prevention) and persistence.
8. Alert engine rule evaluation, severity assignment, ack and resolve workflows.
9. Scientific drift calculation returning INSUFFICIENT_DATA when insufficient samples exist.
10. Dynamic 30-point readiness calculation across CAT-A through CAT-F.
11. Data Health live checks for NCUM, NEPS, and IMD.
12. Safety gate: REAL_OPERATIONAL strictly BLOCKED when required authoritative conditions are not met.
13. FastAPI endpoints for operations and data-health.
"""

import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Ensure src is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from ramp.services.operations_engine import OperationsEngine
from ramp.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def engine():
    """Retrieve OperationsEngine singleton instance."""
    eng = OperationsEngine.get_instance()
    yield eng


def test_engine_singleton(engine):
    """Engine is a singleton instance."""
    eng2 = OperationsEngine.get_instance()
    assert engine is eng2


def test_state_machine_legal_transitions(engine):
    """Engine executes valid state transitions and records them."""
    # Reset/ensure a known state via force_transition
    engine.force_transition("WAITING_FOR_DATA", reason="Test reset")
    curr = engine.get_current_state()
    state_val = curr.value if hasattr(curr, "value") else curr
    assert state_val == "WAITING_FOR_DATA"

    # Legal transition: WAITING_FOR_DATA -> DATA_RECEIVED
    res = engine.transition("DATA_RECEIVED", reason="NCUM received")
    assert res["success"] is True
    assert res["to_state"] == "DATA_RECEIVED"

    # Legal transition: DATA_RECEIVED -> VALIDATING
    res = engine.transition("VALIDATING", reason="Validation started")
    assert res["success"] is True
    assert res["to_state"] == "VALIDATING"

    # Legal transition: VALIDATING -> READY_FOR_INFERENCE
    res = engine.transition("READY_FOR_INFERENCE", reason="QC passed")
    assert res["success"] is True
    assert res["to_state"] == "READY_FOR_INFERENCE"


def test_state_machine_illegal_transition(engine):
    """Engine rejects invalid transitions deterministically."""
    # When in READY_FOR_INFERENCE, cannot jump back to INITIALIZING or DATA_RECEIVED directly
    with pytest.raises(ValueError) as exc:
        engine.transition("INITIALIZING", reason="Invalid jump")
    assert "Illegal transition" in str(exc.value)


def test_transition_history_audit(engine):
    """State transitions are logged with metadata and reason."""
    hist = engine.get_transition_history(limit=5)
    assert isinstance(hist, list)
    assert len(hist) > 0
    latest = hist[0]
    assert "from_state" in latest
    assert "to_state" in latest
    assert "timestamp" in latest
    assert "reason" in latest


def test_operational_cycles_tracking(engine):
    """00Z and 12Z synoptic cycles are created, tracked, and delay/SLA calculated."""
    cycles = engine.list_operational_cycles(limit=10)
    assert len(cycles) > 0
    cycle = cycles[0]
    assert "cycle_id" in cycle
    assert cycle["cycle_type"] in ("00Z", "12Z")
    assert "sla_status" in cycle
    assert cycle["sla_status"] in ("ON_TIME", "DELAYED", "STALE", "MISSING")
    assert "delay_minutes" in cycle
    assert "status" in cycle


def test_cycle_timeline_events(engine):
    """Selecting a cycle returns chronological events."""
    cycles = engine.list_operational_cycles(limit=1)
    assert len(cycles) > 0
    cycle_id = cycles[0]["cycle_id"]

    # Log a test event
    engine.record_cycle_event(
        cycle_id=cycle_id,
        event_type="TEST_CHECKPOINT",
        status="PASS",
        message="Automated pipeline test checkpoint reached",
        source="TEST_SUITE",
    )

    detail = engine.get_cycle_detail(cycle_id)
    assert detail is not None
    assert detail["cycle_id"] == cycle_id
    assert "events" in detail
    assert any(ev["event_type"] == "TEST_CHECKPOINT" for ev in detail["events"])


def test_scheduler_lifecycle_and_persistence(engine):
    """Scheduler start and stop update backend state safely."""
    # Start scheduler
    status_started = engine.start_scheduler()
    assert status_started["is_running"] is True

    sched_status = engine.get_scheduler_status()
    assert sched_status["is_running"] is True
    assert sched_status["scheduler_status"] == "RUNNING"

    # Stop scheduler
    status_stopped = engine.stop_scheduler()
    assert status_stopped["is_running"] is False

    sched_status2 = engine.get_scheduler_status()
    assert sched_status2["is_running"] is False
    assert sched_status2["scheduler_status"] == "STOPPED"


def test_job_submission_and_idempotency(engine):
    """Job submission validates idempotency: duplicate (cycle, lead, model) is skipped."""
    import time
    cycle_id = f"TEST_CYCLE_{int(time.time() * 1000)}_00Z"
    lead = 24
    model_version = "ramp_moe_v2.0.0"

    # First submission
    job1 = engine.submit_forecast_job(cycle_id=cycle_id, lead_hours=lead, model_version=model_version)
    assert job1["status"] in ("QUEUED", "RUNNING", "SUCCESS", "FAILED")
    assert job1["is_duplicate"] is False

    # Second submission with same idempotency key
    job2 = engine.submit_forecast_job(cycle_id=cycle_id, lead_hours=lead, model_version=model_version)
    assert job2["status"] == "SKIPPED_DUPLICATE"
    assert job2["is_duplicate"] is True


def test_alert_rules_and_events(engine):
    """Alert engine evaluates rules and supports acknowledge & resolve."""
    # Check alert rules
    alerts_data = engine.get_alerts_data()
    assert "rules" in alerts_data
    assert len(alerts_data["rules"]) >= 8

    # Create a test alert
    alert = engine.create_alert(
        rule_id="RULE-08-PIPELINE",
        severity="WARNING",
        message="Test alert event for operational pipeline",
        cycle_id="DEMO_20260927_00Z",
    )
    assert alert["alert_id"].startswith("alt-")
    assert alert["status"] == "ACTIVE"

    # Acknowledge
    ack = engine.acknowledge_alert(alert["alert_id"], operator="Sunny")
    assert ack["acknowledged"] is True
    assert ack["status"] == "ACKNOWLEDGED"

    # Resolve
    res = engine.resolve_alert(alert["alert_id"], operator="Sunny")
    assert res["resolved"] is True
    assert res["status"] == "RESOLVED"


def test_drift_monitor_scientific_honesty(engine):
    """Drift calculation returns INSUFFICIENT_DATA when baseline samples < 20."""
    drift = engine.get_drift_measurements(feature_samples={}, prediction_samples=[])
    assert drift["overall_drift_level"] in ("INSUFFICIENT_DATA", "NO_DATA", "NONE")
    for feat in drift["feature_drift"]:
        if feat.get("current_count", 0) < 20:
            assert feat["drift_level"] == "INSUFFICIENT_DATA"


def test_dynamic_readiness_checklist(engine):
    """Readiness checklist dynamically tests CAT-A through CAT-F and computes score."""
    readiness = engine.run_readiness_checks()
    assert readiness["total_checks"] == 30
    assert "passed" in readiness
    assert "overall_status" in readiness
    assert readiness["passed"] >= 0
    assert readiness["overall_status"] in ("GO", "CONDITIONAL_GO", "NO_GO")
    assert "category_summary" in readiness
    assert "CAT-A" in readiness["category_summary"]
    assert "CAT-B" in readiness["category_summary"]


def test_data_health_sources(engine):
    """Data Health returns live checks for NCUM, NEPS, and IMD."""
    sources = engine.get_data_sources_health()
    providers = sources.get("providers", sources)
    assert "NCMRWF_NCUM" in providers
    assert "NCMRWF_NEPS" in providers
    assert "IMD_GRIDDED_OBSERVATION" in providers

    ncum = providers["NCMRWF_NCUM"]
    assert "mounted" in ncum
    assert "availability" in ncum
    assert "qc_status" in ncum


def test_safety_gate_blocking(engine):
    """Operational gate REAL_OPERATIONAL is BLOCKED unless real sources are mounted."""
    status = engine.get_operational_status()
    # In test/local environment without mounted production NCMRWF/IMD NFS shares,
    # gate MUST be blocked!
    assert status["gates"]["real_operational"] is False
    assert status["data_mode"] == "SYNTHETIC_DEMO"


def test_api_endpoints_operations():
    """FastAPI endpoints for operations respond correctly."""
    r_status = client.get("/api/operations/status")
    assert r_status.status_code == 200
    assert "data_mode" in r_status.json()

    r_state = client.get("/api/operations/state")
    assert r_state.status_code == 200
    assert "current_state" in r_state.json()

    r_cycles = client.get("/api/operations/cycles")
    assert r_cycles.status_code == 200
    assert "cycles" in r_cycles.json()

    r_jobs = client.get("/api/operations/jobs")
    assert r_jobs.status_code == 200
    assert "jobs" in r_jobs.json()

    r_alerts = client.get("/api/operations/alerts")
    assert r_alerts.status_code == 200
    assert "rules" in r_alerts.json()


def test_api_endpoints_data_health():
    """FastAPI endpoints for data-health respond correctly."""
    r_sources = client.get("/api/data-health/sources")
    assert r_sources.status_code == 200
    data = r_sources.json()
    assert data["status"] == "SUCCESS"
    payload = data["data"]
    assert "providers" in payload or "sources" in payload

    r_freshness = client.get("/api/data-health/freshness")
    assert r_freshness.status_code == 200
    assert r_freshness.json()["status"] == "SUCCESS"

    r_qc = client.get("/api/data-health/quality")
    assert r_qc.status_code == 200
    assert r_qc.json()["status"] == "SUCCESS"
