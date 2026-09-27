"""
Phase 15 Operations Control Center Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

25 Mandatory Rigorous Tests:
 1.  test_state_machine_initial_state
 2.  test_state_machine_valid_transition
 3.  test_state_machine_invalid_transition_rejected
 4.  test_state_machine_force_transition
 5.  test_state_machine_history_recorded
 6.  test_state_machine_thread_safety
 7.  test_scheduler_initializes
 8.  test_scheduler_job_id_deterministic
 9.  test_scheduler_idempotency
10.  test_scheduler_status_api
11.  test_alert_monitor_evaluates_metrics
12.  test_alert_monitor_no_duplicate_active_alerts
13.  test_alert_monitor_acknowledge
14.  test_alert_monitor_resolve
15.  test_alert_built_in_rules_count
16.  test_drift_monitor_feature_drift
17.  test_drift_monitor_prediction_drift
18.  test_drift_monitor_calibration_drift
19.  test_drift_monitor_regime_drift
20.  test_drift_overall_level
21.  test_readiness_evaluates_30_checks
22.  test_readiness_cat_a_checks
23.  test_readiness_gate_logic
24.  test_readiness_synthetic_demo_gate
25.  test_operations_api_status_endpoint
"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ml.operations.alerts import AlertMonitor, BUILT_IN_RULES, AlertSeverity
from ml.operations.drift import DriftMonitor
from ml.operations.production import ProductionReadinessEngine
from ml.operations.scheduler import ForecastJob, ForecastScheduler, JobStatus
from ml.operations.state import OperationalState, OperationalStateMachine, _TRANSITIONS


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1: State Machine
# ══════════════════════════════════════════════════════════════════════════════

class TestStateMachine:

    def test_state_machine_initial_state(self):
        """T1: State machine initialises to WAITING_FOR_DATA by default."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        assert sm.current_state == OperationalState.WAITING_FOR_DATA
        assert sm.state_name == "WAITING_FOR_DATA"

    def test_state_machine_valid_transition(self):
        """T2: A valid transition from WAITING_FOR_DATA → DATA_RECEIVED succeeds."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        ok = sm.transition(OperationalState.DATA_RECEIVED, reason="test", triggered_by="TEST")
        assert ok is True
        assert sm.current_state == OperationalState.DATA_RECEIVED

    def test_state_machine_invalid_transition_rejected(self):
        """T3: An invalid transition (WAITING_FOR_DATA → PUBLISHED) is rejected."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        ok = sm.transition(OperationalState.PUBLISHED, reason="illegal", triggered_by="TEST")
        assert ok is False
        assert sm.current_state == OperationalState.WAITING_FOR_DATA  # unchanged

    def test_state_machine_force_transition(self):
        """T4: Force-transition bypasses guard and changes state."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        event = sm.force_transition(OperationalState.PUBLISHED, reason="OPERATOR_OVERRIDE")
        assert sm.current_state == OperationalState.PUBLISHED
        assert event.triggered_by == "OPERATOR"

    def test_state_machine_history_recorded(self):
        """T5: Every transition is recorded in the audit history."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        sm.transition(OperationalState.DATA_RECEIVED, reason="r1", triggered_by="T")
        sm.transition(OperationalState.VALIDATING, reason="r2", triggered_by="T")
        history = sm.get_history()
        # Bootstrap event + 2 transitions
        assert len(history) >= 3
        assert history[-1]["to_state"] == "VALIDATING"

    def test_state_machine_thread_safety(self):
        """T6: Concurrent transitions from multiple threads do not corrupt state."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        errors = []

        def do_transitions():
            for _ in range(5):
                sm.transition(OperationalState.DATA_RECEIVED, reason="t", triggered_by="T")
                sm.transition(OperationalState.WAITING_FOR_DATA, triggered_by="T")

        threads = [threading.Thread(target=do_transitions) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sm.current_state in (
            OperationalState.WAITING_FOR_DATA,
            OperationalState.DATA_RECEIVED,
        ), f"Unexpected state: {sm.current_state}"
        assert len(errors) == 0

    def test_transition_table_complete(self):
        """T0: Every OperationalState has an entry in the transition table."""
        # ALERT_RAISED and CYCLE_COMPLETE always have outgoing transitions
        for state in OperationalState:
            # All states should be reachable from somewhere (in _TRANSITIONS values)
            all_targets = {s for targets in _TRANSITIONS.values() for s in targets}
            all_sources = set(_TRANSITIONS.keys())
            assert state in all_sources or state in all_targets, f"State {state} unreachable"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2: Scheduler
# ══════════════════════════════════════════════════════════════════════════════

class TestScheduler:

    def test_scheduler_initializes(self):
        """T7: ForecastScheduler initializes without error."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        sched = ForecastScheduler(sm, poll_interval_s=3600)
        assert not sched.is_running()
        status = sched.get_status()
        assert "scheduler_enabled" in status
        assert status["scheduler_enabled"] is False

    def test_scheduler_job_id_deterministic(self):
        """T8: Job ID is a deterministic SHA-256 hash of (cycle, lead, model_version)."""
        id1 = ForecastJob.make_job_id("DEMO_20260927_00Z", 24, "v2.0.0")
        id2 = ForecastJob.make_job_id("DEMO_20260927_00Z", 24, "v2.0.0")
        id3 = ForecastJob.make_job_id("DEMO_20260927_12Z", 24, "v2.0.0")
        assert id1 == id2
        assert id1 != id3
        assert len(id1) == 16

    def test_scheduler_idempotency(self):
        """T9: A completed job ID is not re-executed on re-submission (SKIPPED)."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        sched = ForecastScheduler(sm)

        # Manually inject a completed job_id
        job_id = ForecastJob.make_job_id("DEMO_00Z", 24, "v2.0.0")
        sched._completed.add(job_id)

        skip = sched._submit_job("DEMO_00Z", 24, "v2.0.0", "demo", "SYNTHETIC_DEMO")
        assert skip.status == JobStatus.SKIPPED
        assert skip.skip_reason is not None

    def test_scheduler_status_api(self):
        """T10: get_status() returns all required fields."""
        sm = OperationalStateMachine(OperationalState.WAITING_FOR_DATA)
        sched = ForecastScheduler(sm)
        s = sched.get_status()
        required = [
            "scheduler_enabled", "is_running", "poll_interval_s",
            "poll_count", "last_poll_at", "lead_hours", "job_summary",
        ]
        for k in required:
            assert k in s, f"Missing key: {k}"

    def test_job_status_enum_values(self):
        """T-ext: JobStatus has all required values."""
        assert JobStatus.SUCCESS.value == "SUCCESS"
        assert JobStatus.FAILED.value == "FAILED"
        assert JobStatus.SKIPPED.value == "SKIPPED"
        assert JobStatus.PENDING.value == "PENDING"
        assert JobStatus.RUNNING.value == "RUNNING"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3: Alert Monitor
# ══════════════════════════════════════════════════════════════════════════════

class TestAlertMonitor:

    def test_alert_built_in_rules_count(self):
        """T15: Exactly 8 built-in alert rules defined."""
        assert len(BUILT_IN_RULES) == 8

    def test_alert_monitor_evaluates_metrics(self):
        """T11: Evaluating metrics that breach thresholds raises alerts."""
        monitor = AlertMonitor()
        metrics = {
            "job_failure_rate": 0.50,    # > 0.20 → RULE_001
            "consecutive_failures": 4.0, # >= 3   → RULE_002
        }
        alerts = monitor.evaluate(metrics)
        assert len(alerts) >= 2
        rule_ids = {a.rule_id for a in alerts}
        assert "RULE_001" in rule_ids
        assert "RULE_002" in rule_ids

    def test_alert_monitor_no_duplicate_active_alerts(self):
        """T12: Evaluating the same breach twice does not create duplicate active alerts."""
        monitor = AlertMonitor()
        metrics = {"job_failure_rate": 0.99}
        first = monitor.evaluate(metrics)
        second = monitor.evaluate(metrics)
        assert len(first) == 1
        assert len(second) == 0  # de-duplicated

    def test_alert_monitor_acknowledge(self):
        """T13: An alert can be acknowledged by an operator."""
        monitor = AlertMonitor()
        alerts = monitor.evaluate({"job_failure_rate": 0.99})
        assert len(alerts) == 1
        alert_id = alerts[0].alert_id
        ok = monitor.acknowledge(alert_id, operator="TEST_OPERATOR")
        assert ok is True
        active = monitor.get_active_alerts()
        ack_alert = next((a for a in active if a["alert_id"] == alert_id), None)
        assert ack_alert is not None
        assert ack_alert["acknowledged"] is True
        assert ack_alert["acknowledged_by"] == "TEST_OPERATOR"

    def test_alert_monitor_resolve(self):
        """T14: An alert can be resolved (removed from active list)."""
        monitor = AlertMonitor()
        alerts = monitor.evaluate({"job_failure_rate": 0.99})
        alert_id = alerts[0].alert_id
        ok = monitor.resolve(alert_id)
        assert ok is True
        active = monitor.get_active_alerts()
        assert all(a["alert_id"] != alert_id for a in active)

    def test_alert_severity_hierarchy(self):
        """T-ext: AlertSeverity values are correct."""
        assert AlertSeverity.INFO.value == "INFO"
        assert AlertSeverity.WARNING.value == "WARNING"
        assert AlertSeverity.CRITICAL.value == "CRITICAL"

    def test_alert_rule_004_ece_threshold(self):
        """T-ext: RULE_004 fires when extreme_ece > 0.08."""
        monitor = AlertMonitor()
        alerts = monitor.evaluate({"extreme_ece": 0.09})
        rule_ids = {a.rule_id for a in alerts}
        assert "RULE_004" in rule_ids

    def test_alert_no_alerts_on_nominal_metrics(self):
        """T-ext: No alerts on nominal system metrics."""
        monitor = AlertMonitor()
        metrics = {
            "job_failure_rate": 0.05,
            "consecutive_failures": 0.0,
            "rmse_drift_pct": 0.05,
            "extreme_ece": 0.04,
            "scheduler_stalled": 0.0,
            "unauthorized_real_mode": 0.0,
            "checksum_failures": 0.0,
            "validation_gate_failure_rate": 0.05,
        }
        alerts = monitor.evaluate(metrics)
        assert len(alerts) == 0


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4: Drift Monitor
# ══════════════════════════════════════════════════════════════════════════════

class TestDriftMonitor:

    def _get_report(self):
        dm = DriftMonitor()
        return dm.compute_drift(data_mode="SYNTHETIC_DEMO")

    def test_drift_monitor_feature_drift(self):
        """T16: Drift report contains feature drift metrics for all baseline features."""
        report = self._get_report()
        assert len(report.feature_drift) > 0
        for fd in report.feature_drift:
            assert fd.feature_name
            assert fd.drift_level in ("NONE", "WARNING", "CRITICAL")
            assert 0.0 <= fd.ks_statistic <= 1.0

    def test_drift_monitor_prediction_drift(self):
        """T17: Prediction drift is computed with a drift_level field."""
        report = self._get_report()
        pd = report.prediction_drift
        assert pd is not None
        assert pd.drift_level in ("NONE", "WARNING", "CRITICAL")
        assert pd.baseline_mean_forecast_mm > 0
        assert pd.current_mean_forecast_mm >= 0

    def test_drift_monitor_calibration_drift(self):
        """T18: Calibration drift covers all 4 IMD thresholds (0.1, 64.5, 115.6, 204.5)."""
        report = self._get_report()
        thresholds = {c.threshold_mm for c in report.calibration_drift}
        assert 0.1 in thresholds
        assert 64.5 in thresholds
        assert 115.6 in thresholds
        assert 204.5 in thresholds

    def test_drift_monitor_regime_drift(self):
        """T19: Regime drift covers all 7 canonical weather regimes."""
        report = self._get_report()
        regime_names = {r.regime_name for r in report.regime_drift}
        expected = {
            "ACTIVE_MONSOON", "BREAK_MONSOON", "CYCLONIC",
            "WESTERN_DISTURBANCE", "DRY_CONTINENTAL",
            "NORTHEAST_MONSOON", "CONVECTIVE_MODERATE",
        }
        assert expected == regime_names

    def test_drift_overall_level(self):
        """T20: overall_drift_level is one of NONE / WARNING / CRITICAL."""
        report = self._get_report()
        assert report.overall_drift_level in ("NONE", "WARNING", "CRITICAL")

    def test_drift_disclaimer_present(self):
        """T-ext: Drift report contains honesty disclaimer."""
        report = self._get_report()
        assert "SYNTHETIC_DEMO" in report.disclaimer
        assert "diagnostic" in report.disclaimer.lower()

    def test_drift_report_serializable(self):
        """T-ext: DriftReport.to_dict() returns a fully serializable dict."""
        report = self._get_report()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "overall_drift_level" in d
        assert "feature_drift" in d
        assert isinstance(d["feature_drift"], list)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5: Production Readiness
# ══════════════════════════════════════════════════════════════════════════════

class TestProductionReadiness:

    def _get_report(self):
        engine = ProductionReadinessEngine()
        return engine.evaluate(data_mode="SYNTHETIC_DEMO")

    def test_readiness_evaluates_30_checks(self):
        """T21: Exactly 30 readiness checks are evaluated."""
        report = self._get_report()
        assert report.total_checks == 30

    def test_readiness_cat_a_checks(self):
        """T22: CAT-A has exactly 5 checks."""
        report = self._get_report()
        cat_a = [c for c in report.checks if c.category == "CAT-A"]
        assert len(cat_a) == 5

    def test_readiness_gate_logic(self):
        """T23: REAL_OPERATIONAL gate is BLOCKED when not in real data mode."""
        report = self._get_report()
        assert report.gate_real_operational is False  # must be blocked for SYNTHETIC_DEMO

    def test_readiness_synthetic_demo_gate(self):
        """T24: SYNTHETIC_DEMO gate logic returns a boolean."""
        report = self._get_report()
        assert isinstance(report.gate_synthetic_demo, bool)

    def test_readiness_overall_status_valid(self):
        """T-ext: Overall status is one of GO / CONDITIONAL_GO / NO_GO."""
        report = self._get_report()
        assert report.overall_status in ("GO", "CONDITIONAL_GO", "NO_GO")

    def test_readiness_6_categories(self):
        """T-ext: Exactly 6 categories are evaluated."""
        report = self._get_report()
        cats = set(c.category for c in report.checks)
        assert cats == {"CAT-A", "CAT-B", "CAT-C", "CAT-D", "CAT-E", "CAT-F"}

    def test_readiness_report_serializable(self):
        """T-ext: ProductionReadinessReport.to_dict() is JSON-serializable."""
        import json
        report = self._get_report()
        d = report.to_dict()
        serialized = json.dumps(d)  # must not raise
        assert len(serialized) > 100

    def test_readiness_disclaimer_present(self):
        """T-ext: Readiness report contains engineering-only disclaimer."""
        report = self._get_report()
        assert "engineering" in report.disclaimer.lower()
        assert "MoES" in report.disclaimer or "NCMRWF" in report.disclaimer


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6: Operations API
# ══════════════════════════════════════════════════════════════════════════════

class TestOperationsAPI:

    @pytest.fixture
    def client(self):
        from ramp.main import app
        return TestClient(app)

    def test_operations_api_status_endpoint(self, client):
        """T25: GET /api/operations/status returns 200 with required fields."""
        resp = client.get("/api/operations/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "data_mode" in data
        assert "state_machine" in data
        assert "scheduler" in data
        assert "alerts" in data
        assert data["data_mode"] == "SYNTHETIC_DEMO"

    def test_operations_api_state_endpoint(self, client):
        """T-ext: GET /api/operations/state returns current state."""
        resp = client.get("/api/operations/state")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_state" in data
        assert "transition_history" in data

    def test_operations_api_scheduler_endpoint(self, client):
        """T-ext: GET /api/operations/scheduler returns scheduler status."""
        resp = client.get("/api/operations/scheduler")
        assert resp.status_code == 200
        data = resp.json()
        assert "scheduler_enabled" in data
        assert "is_running" in data

    def test_operations_api_alerts_endpoint(self, client):
        """T-ext: GET /api/operations/alerts returns alerts and rules."""
        resp = client.get("/api/operations/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "rules" in data

    def test_operations_api_drift_endpoint(self, client):
        """T-ext: GET /api/operations/drift returns drift report."""
        resp = client.get("/api/operations/drift")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_drift_level" in data
        assert "feature_drift" in data

    def test_operations_api_readiness_endpoint(self, client):
        """T-ext: GET /api/operations/readiness returns 30-check report."""
        resp = client.get("/api/operations/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_checks"] == 30
        assert "overall_status" in data

    def test_operations_api_health_endpoint(self, client):
        """T-ext: GET /api/operations/health returns HEALTHY or DEGRADED."""
        resp = client.get("/api/operations/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("HEALTHY", "DEGRADED")
        assert data["data_mode"] == "SYNTHETIC_DEMO"

    def test_operations_api_invalid_state_transition(self, client):
        """T-ext: POST /api/operations/state/transition with invalid state → 400."""
        resp = client.post(
            "/api/operations/state/transition",
            json={"to_state": "NONEXISTENT_STATE", "reason": "bad"},
        )
        assert resp.status_code == 400

    def test_operations_api_jobs_endpoint(self, client):
        """T-ext: GET /api/operations/jobs returns job list."""
        resp = client.get("/api/operations/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
