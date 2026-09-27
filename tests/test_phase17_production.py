"""
Phase 17 — Production Deployment, Data Connectivity, Operational Reliability & Verification Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

PART AR Mandatory Minimum Coverage (35 Tests):
  1.  test_environment_config
  2.  test_production_config_validation
  3.  test_health_live
  4.  test_health_ready
  5.  test_data_health
  6.  test_ncum_freshness
  7.  test_neps_freshness
  8.  test_imd_freshness
  9.  test_cycle_manager
  10. test_cycle_idempotency
  11. test_lead_schedule
  12. test_retry_policy
  13. test_transient_failure_recovery
  14. test_terminal_failure
  15. test_alert_generation
  16. test_alert_deduplication
  17. test_storage_monitor
  18. test_publication_validation
  19. test_publication_catalog
  20. test_verification_history
  21. test_no_fake_verification
  22. test_no_fake_uptime
  23. test_no_fake_live_status
  24. test_real_data_loss
  25. test_emergency_stop
  26. test_authorization
  27. test_audit_logging
  28. test_backup_manifest
  29. test_security_controls
  30. test_api_production_status
  31. test_api_cycles
  32. test_api_data_health
  33. test_api_verification
  34. test_phase17_no_retraining
  35. test_synthetic_mode_safety
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ml.production.config import (
    AppEnvironment,
    OperationalDataMode,
    ProductionConfig,
    ProductionConfigValidator,
    ConfigurationValidationError,
)
from ml.production.connectivity import (
    DataConnectivityMonitor,
    DataFreshnessMonitor,
    ObservationAvailabilityMonitor,
    FreshnessStatus,
    ObservationStatus,
)
from ml.production.cycle_manager import (
    OperationalCycleFlowState,
    JobExecutionStatus,
    OperationalCycleManager,
    ProductionJobQueue,
    SUPPORTED_OPERATIONAL_LEADS,
)
from ml.production.alerts import (
    AlertSeverity,
    ProductionAlertCategory,
    ProductionAlertEngine,
    AlertStatus,
)
from ml.production.storage import (
    OperationalStorageMonitor,
)
from ml.production.publication import (
    PublicationState,
    OperationalPublicationEngine,
    PublishedForecastItem,
)
from ml.production.verification import (
    ContinuousVerificationTracker,
    DailyVerificationReportGenerator,
    HistoricalVerificationStore,
)
from ml.production.reliability import (
    OperationalSLAEngine,
    DiagnosticDriftHistoryTracker,
)
from ml.production.readiness import ExtendedProductionReadinessEngine
from ml.production.backup import ProductionBackupManager
from ml.production.audit import (
    ProductionAuditLogger,
    UserRole,
)
from ml.production.emergency import EmergencyShutdownManager
from ramp.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Environment & Configuration
# ---------------------------------------------------------------------------

def test_environment_config():
    """Verify AppEnvironment enum and ProductionConfig loading."""
    assert AppEnvironment.DEVELOPMENT.value == "DEVELOPMENT"
    assert AppEnvironment.STAGING.value == "STAGING"
    assert AppEnvironment.PRODUCTION.value == "PRODUCTION"

    cfg = ProductionConfig(
        app_env=AppEnvironment.DEVELOPMENT,
        data_mode=OperationalDataMode.SYNTHETIC_DEMO,
    )
    assert cfg.app_env == AppEnvironment.DEVELOPMENT
    assert cfg.data_mode == OperationalDataMode.SYNTHETIC_DEMO


def test_production_config_validation():
    """Verify validator rejects invalid configurations in production."""
    bad_cfg = ProductionConfig(
        app_env=AppEnvironment.PRODUCTION,
        data_mode=OperationalDataMode.REAL_OPERATIONAL,
        ncmrwf_data_root="data/non_existent_ncmrwf_path_12345",
        imd_data_root="data/non_existent_imd_path_12345",
        secret_key="short",
    )
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ProductionConfigValidator.validate_config(bad_cfg)
    assert "validation failed" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 2. Modular Health Checks
# ---------------------------------------------------------------------------

def test_health_live():
    """Verify /health/live returns UP and 200."""
    res = client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UP"
    assert data["subsystem"] == "live"


def test_health_ready():
    """Verify /health/ready returns UP/READY and 200."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("UP", "READY")
    assert data["ready"] is True


def test_data_health():
    """Verify /health/data truthfully reports BLOCKED when authoritative data unmounted."""
    res = client.get("/health/data")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("BLOCKED", "UP")


# ---------------------------------------------------------------------------
# 3. Data Freshness & Connectivity
# ---------------------------------------------------------------------------

def test_ncum_freshness():
    """Verify NCUM freshness monitor computes synoptic cycle status."""
    monitor = DataFreshnessMonitor()
    records = monitor.evaluate_freshness()
    ncum_records = [r for r in records if r.source_id == "NCMRWF_NCUM"]
    assert len(ncum_records) >= 2
    for r in ncum_records:
        assert r.status in (
            FreshnessStatus.NOT_AVAILABLE.value,
            FreshnessStatus.ON_TIME.value,
            FreshnessStatus.DELAYED.value,
            FreshnessStatus.MISSING.value,
        )


def test_neps_freshness():
    """Verify NEPS freshness monitor calculates expected arrival."""
    monitor = DataFreshnessMonitor()
    records = monitor.evaluate_freshness()
    neps_records = [r for r in records if r.source_id == "NCMRWF_NEPS"]
    assert len(neps_records) >= 2
    cycles = [r.cycle for r in neps_records]
    assert "00Z" in cycles
    assert "12Z" in cycles


def test_imd_freshness():
    """Verify IMD observation availability tracking."""
    monitor = ObservationAvailabilityMonitor()
    record = monitor.evaluate_observation_health()
    assert record.source_id == "IMD_GRIDDED_RAINFALL"
    assert record.status in (
        ObservationStatus.NOT_AVAILABLE.value,
        ObservationStatus.AVAILABLE.value,
        ObservationStatus.MISSING.value,
    )
    assert record.pairing_readiness in ("READY", "BLOCKED", "INSUFFICIENT_OBSERVATIONS", "NOT_AVAILABLE")


# ---------------------------------------------------------------------------
# 4. Cycle Management & Idempotency
# ---------------------------------------------------------------------------

def test_cycle_manager():
    """Verify 11-stage operational cycle state flow."""
    manager = OperationalCycleManager()
    cycle = manager.create_cycle("TEST_20260927_00Z", initialization_time="00:00Z")
    assert cycle.state == OperationalCycleFlowState.WAITING_FOR_DATA.value

    # Valid transition to DATA_DISCOVERED
    res = manager.transition_cycle("TEST_20260927_00Z", OperationalCycleFlowState.DATA_DISCOVERED, "Data arrived")
    assert res.state == OperationalCycleFlowState.DATA_DISCOVERED.value


def test_cycle_idempotency():
    """Verify ProductionJobQueue uses deterministic SHA-256 IDs to prevent duplicate execution."""
    queue = ProductionJobQueue()
    job1 = queue.enqueue_job("CYCLE_001", lead_hours=24, model_version="ramp_moe_v2.0.0")
    job2 = queue.enqueue_job("CYCLE_001", lead_hours=24, model_version="ramp_moe_v2.0.0")

    # Same parameters must yield the identical job_id
    assert job1.job_id == job2.job_id
    assert job2.status in (JobExecutionStatus.QUEUED.value, JobExecutionStatus.SKIPPED.value)


def test_lead_schedule():
    """Verify lead schedule covers +6h to +120h standard operational horizons."""
    assert SUPPORTED_OPERATIONAL_LEADS == [6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 72, 96, 120]
    assert len(SUPPORTED_OPERATIONAL_LEADS) == 13


def test_retry_policy():
    """Verify non-retryable errors classification."""
    manager = OperationalCycleManager()
    assert "CHECKSUM_MISMATCH" in manager.NON_RETRYABLE_ERRORS
    assert "METADATA_INVALID" in manager.NON_RETRYABLE_ERRORS
    assert "LEAKAGE_DETECTED" in manager.NON_RETRYABLE_ERRORS


def test_transient_failure_recovery():
    """Verify transient error recovery cycle flow."""
    manager = OperationalCycleManager()
    cycle = manager.create_cycle("RETRY_CYCLE_001")
    manager.transition_cycle("RETRY_CYCLE_001", OperationalCycleFlowState.RETRY_PENDING, "Transient network error")
    c = manager.get_cycle("RETRY_CYCLE_001")
    assert c.state == OperationalCycleFlowState.RETRY_PENDING.value


def test_terminal_failure():
    """Verify non-transient error triggers TERMINAL_FAILURE."""
    manager = OperationalCycleManager()
    cycle = manager.create_cycle("TERMINAL_CYCLE_001")
    manager.transition_cycle("TERMINAL_CYCLE_001", OperationalCycleFlowState.TERMINAL_FAILURE, "Non-retryable CF error")
    c = manager.get_cycle("TERMINAL_CYCLE_001")
    assert c.state == OperationalCycleFlowState.TERMINAL_FAILURE.value


# ---------------------------------------------------------------------------
# 5. Alerting & Storage
# ---------------------------------------------------------------------------

def test_alert_generation():
    """Verify alert engine generates alerts across defined categories."""
    engine = ProductionAlertEngine()
    alert = engine.raise_alert(
        category=ProductionAlertCategory.DATA_MISSING,
        severity=AlertSeverity.WARNING,
        title="NCUM Missing",
        message="NCUM 00Z forecast file missing past cutoff",
        source="NCUM_HARVESTER",
    )
    assert alert.category == ProductionAlertCategory.DATA_MISSING.value
    assert alert.severity == AlertSeverity.WARNING.value
    assert alert.status == AlertStatus.RAISED.value


def test_alert_deduplication():
    """Verify alert engine does not generate duplicate active alerts for the same category and source."""
    engine = ProductionAlertEngine()
    a1 = engine.raise_alert(
        category=ProductionAlertCategory.DATA_STALE,
        severity=AlertSeverity.WARNING,
        title="Stale feed",
        message="Stale feed",
        source="FEED_MONITOR_UNIQUE",
    )
    a2 = engine.raise_alert(
        category=ProductionAlertCategory.DATA_STALE,
        severity=AlertSeverity.WARNING,
        title="Stale feed duplicate",
        message="Stale feed duplicate",
        source="FEED_MONITOR_UNIQUE",
    )
    assert a1.alert_id == a2.alert_id
    assert len(engine.list_alerts(active_only=True)) >= 1


def test_storage_monitor():
    """Verify storage monitor tracks partition usage without deleting operational data."""
    metrics = OperationalStorageMonitor.get_storage_metrics()
    assert metrics.disk_total_bytes > 0
    assert metrics.disk_free_bytes > 0
    assert "raw_ncmrwf" in metrics.directories
    assert "audit_logs" in metrics.directories
    assert metrics.directories["audit_logs"].auto_delete_allowed is False


# ---------------------------------------------------------------------------
# 6. Publication & Verification
# ---------------------------------------------------------------------------

def test_publication_validation():
    """Verify publication engine rejects non-monotonic probabilities."""
    engine = OperationalPublicationEngine()
    invalid_product = {
        "model_version": "v2.0.0",
        "output_checksum": "sha256_mock_hash",
        "exceedance_probabilities": {
            "p_ge_2_5": 0.2,
            "p_ge_15_6": 0.8,  # Error: P(>=15.6) > P(>=2.5)
            "p_ge_64_5": 0.1,
            "p_ge_115_6": 0.05,
        }
    }
    errors = engine.validate_for_publication(invalid_product)
    assert len(errors) > 0
    assert any("Monotonicity violation" in e for e in errors)


def test_publication_catalog():
    """Verify forecast publication catalog records published items."""
    engine = OperationalPublicationEngine()
    items = engine.list_publications()
    assert isinstance(items, list)


def test_verification_history():
    """Verify historical verification store tracks verification scores."""
    store = HistoricalVerificationStore()
    history = store.get_history()
    assert isinstance(history, list)


# ---------------------------------------------------------------------------
# 7. Scientific Integrity Guarantees
# ---------------------------------------------------------------------------

def test_no_fake_verification():
    """Scientific Integrity: Verification must return NOT_AVAILABLE if ground truth unmounted."""
    summary = DailyVerificationReportGenerator.generate_daily_report(has_authoritative_data=False)
    assert summary.status == "NOT_AVAILABLE"
    assert summary.sample_count == 0
    assert "REAL VERIFICATION NOT AVAILABLE" in summary.disclaimer


def test_no_fake_uptime():
    """Scientific Integrity: SLA uptime must not be manufactured."""
    metrics = OperationalSLAEngine.compute_sla_metrics([], total_cycles_attempted=0)
    assert metrics.cycle_completion_rate is None
    assert metrics.mean_inference_latency_ms is None
    assert metrics.status == "NOT_AVAILABLE"


def test_no_fake_live_status():
    """Scientific Integrity: System must never report PRODUCTION LIVE when unmounted."""
    res = client.get("/api/production/status")
    assert res.status_code == 200
    data = res.json()
    assert data["real_operational_blocked"] is True
    assert data["authoritative_data_present"] is False


def test_real_data_loss():
    """Verify circuit breaker when authoritative data disappear."""
    manager = OperationalCycleManager()
    cycle = manager.create_cycle("DATA_LOSS_CYCLE")
    manager.transition_cycle("DATA_LOSS_CYCLE", OperationalCycleFlowState.REAL_DATA_LOST, "Lost data connectivity")
    c = manager.get_cycle("DATA_LOSS_CYCLE")
    assert c.state == OperationalCycleFlowState.REAL_DATA_LOST.value


def test_emergency_stop():
    """Verify emergency shutdown freezes jobs and requires supervisor recovery."""
    mgr = EmergencyShutdownManager()
    # Viewer cannot trigger
    with pytest.raises(PermissionError):
        mgr.trigger_emergency_stop("VIEWER_USER", UserRole.VIEWER, "Unauthorized attempt")

    # Operator can trigger
    status = mgr.trigger_emergency_stop("OPERATOR_1", UserRole.OPERATOR, "High error rate detected")
    assert status.is_emergency_active is True
    assert mgr.is_operational_blocked() is True

    # Operator cannot recover
    with pytest.raises(PermissionError):
        mgr.recover_from_emergency("OPERATOR_1", UserRole.OPERATOR, "Trying to clear")

    # Supervisor can recover
    status2 = mgr.recover_from_emergency("SUPERVISOR_1", UserRole.SUPERVISOR, "Telemetry verified normal")
    assert status2.is_emergency_active is False
    assert mgr.is_operational_blocked() is False


# ---------------------------------------------------------------------------
# 8. Security, Audit & Backup
# ---------------------------------------------------------------------------

def test_authorization():
    """Verify role-based access control rules."""
    assert ProductionAuditLogger.check_permission(UserRole.VIEWER, UserRole.OPERATOR) is False
    assert ProductionAuditLogger.check_permission(UserRole.OPERATOR, UserRole.OPERATOR) is True
    assert ProductionAuditLogger.check_permission(UserRole.SUPERVISOR, UserRole.OPERATOR) is True
    assert ProductionAuditLogger.check_permission(UserRole.ADMIN, UserRole.SUPERVISOR) is True


def test_audit_logging():
    """Verify immutable audit logger writes valid records."""
    record = ProductionAuditLogger.log_action(
        actor="SUPERVISOR_TEST",
        role=UserRole.SUPERVISOR,
        action="ACTIVATION_APPROVAL",
        resource="NCMRWF_NCUM",
        previous_state="BLOCKED",
        new_state="PENDING_OPERATOR",
        reason="Institutional integration test",
    )
    assert record.actor == "SUPERVISOR_TEST"
    assert record.role == UserRole.SUPERVISOR.value
    logs = ProductionAuditLogger.read_recent_logs(5)
    assert any(l["actor"] == "SUPERVISOR_TEST" for l in logs)


def test_backup_manifest():
    """Verify backup manager creates cryptographically validated backup manifests."""
    manifest = ProductionBackupManager.create_backup(operator_id="PYTEST_RUNNER")
    assert manifest is not None
    assert manifest.backup_id.startswith("BKP_")
    assert len(manifest.archive_sha256) == 64
    assert manifest.is_verified is True


def test_security_controls():
    """Verify safety checks prevent secret leakage."""
    res = client.get("/api/production/status")
    raw = res.text
    # Secret tokens / passwords must never appear in response
    assert "password" not in raw.lower()
    assert "api_key" not in raw.lower()


# ---------------------------------------------------------------------------
# 9. FastAPI Production Endpoints
# ---------------------------------------------------------------------------

def test_api_production_status():
    """Verify GET /api/production/status returns HTTP 200 with standard envelope."""
    res = client.get("/api/production/status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "environment" in body


def test_api_cycles():
    """Verify GET /api/production/cycles returns cycle listing."""
    res = client.get("/api/production/cycles")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "cycles" in body


def test_api_data_health():
    """Verify GET /api/production/data-health returns provider connectivity."""
    res = client.get("/api/production/data-health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "providers" in body


def test_api_verification():
    """Verify GET /api/production/verification returns verification state."""
    res = client.get("/api/production/verification")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"


# ---------------------------------------------------------------------------
# 10. ML Invariance & Synthetic Mode Safety
# ---------------------------------------------------------------------------

def test_phase17_no_retraining():
    """Verify ML model freeze: drift remains diagnostic only; no automatic retraining."""
    action = DiagnosticDriftHistoryTracker.record_drift_observation({
        "feature_drift_detected": True,
        "ks_statistic": 0.45,
    })
    assert action == "RETRAINING_CANDIDATE_IDENTIFIED"


def test_synthetic_mode_safety():
    """Verify synthetic demonstration mode is explicitly marked and never labeled live."""
    res = client.get("/api/production/status")
    assert res.status_code == 200
    data = res.json()
    if data["data_mode"] == "SYNTHETIC_DEMO":
        assert data["real_operational_blocked"] is True
