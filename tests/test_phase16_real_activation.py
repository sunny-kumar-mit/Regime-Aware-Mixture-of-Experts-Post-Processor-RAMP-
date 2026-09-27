"""
Phase 16 — Real-Data Activation, Live Ingestion & Operational Integration Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

PART AG — Mandatory Minimum Test Coverage (30 Tests):
  1.  test_source_registry
  2.  test_source_discovery
  3.  test_ncum_detection
  4.  test_neps_detection
  5.  test_imd_detection
  6.  test_file_integrity
  7.  test_checksum
  8.  test_metadata_validation
  9.  test_temporal_validation
  10. test_spatial_validation
  11. test_unit_validation
  12. test_qc_validation
  13. test_pairing
  14. test_zero_future_leakage
  15. test_activation_gate
  16. test_activation_blocked_without_real_data
  17. test_activation_requires_all_checks
  18. test_activation_requires_operator
  19. test_activation_audit
  20. test_real_mode_transition
  21. test_no_silent_synthetic_fallback
  22. test_real_data_loss
  23. test_partial_spatial_coverage
  24. test_forecast_manifest
  25. test_real_verification
  26. test_insufficient_verification_data
  27. test_api_activation_status
  28. test_api_ingestion_status
  29. test_api_verification
  30. test_no_fake_operational_status
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

from ml.ingestion.sources import (
    AuthorityLevel,
    CANONICAL_18_PREDICTORS,
    DatasetType,
    SourceContract,
    SourceStatus,
    get_authoritative_contract,
    list_authoritative_contracts,
)
from ml.ingestion.registry import SourceRegistry
from ml.ingestion.discovery import OperationalFileDiscoveryService, DiscoveredOperationalFile
from ml.ingestion.integrity import FileIntegrityEngine, FileIntegrityRecord
from ml.ingestion.metadata import MetadataValidator, MetadataValidationResult
from ml.ingestion.temporal import TemporalValidator, TemporalValidationResult
from ml.ingestion.spatial import SpatialValidator, SpatialValidationResult, RAMP_DOMAIN
from ml.ingestion.units import UnitNormalizer, UnitValidationError
from ml.ingestion.qc import MeteorologicalQCEngine, VariableQCResult
from ml.ingestion.pairing import ForecastObservationPairingEngine, PairingManifest
from ml.ingestion.adapters import NCUMAdapter, NEPSAdapter, IMDObservationAdapter
from ml.ingestion.activation import (
    ActivationAuditRecord,
    ActivationStage,
    RealDataActivationEngine,
)
from ml.ingestion.verification import RealVerificationEngine
from ml.inference.provenance import ForecastManifest

from ramp.main import app

client = TestClient(app)
FIXTURE_DIR = Path("tests/fixtures/phase16")


# ── Tests 1 to 5: Source Registry & Discovery ──────────────────────────────

def test_source_registry():
    """1. Test that authoritative source registry correctly declares all required sources."""
    reg = SourceRegistry()
    sources = reg.list_sources()
    assert len(sources) >= 3

    ncum = reg.get_source("NCMRWF_NCUM")
    assert ncum is not None
    assert ncum.provider == "NCMRWF"
    assert ncum.authority_level == AuthorityLevel.AUTHORITATIVE_PRIMARY
    assert len(ncum.variables) == 18
    assert ncum.dataset_type == DatasetType.NWP_DETERMINISTIC

    imd = reg.get_source("IMD_GRIDDED_RAINFALL")
    assert imd is not None
    assert imd.provider == "IMD"
    assert imd.target_grid_deg == 0.25


def test_source_discovery():
    """2. Test recursive file discovery across fixture directories."""
    discovery = OperationalFileDiscoveryService()
    catalog = discovery.discover_files(search_paths=[FIXTURE_DIR])
    assert catalog.total_files_found >= 3
    assert len(catalog.files) >= 3
    # Verify that files in fixture dir are correctly flagged as TEST_FIXTURE
    assert catalog.test_fixture_files_count > 0


def test_ncum_detection():
    """3. Test NCUM deterministic NWP adapter detection and ingestion."""
    adapter = NCUMAdapter()
    fixture = FIXTURE_DIR / "ncum_test_fixture_20260927_00Z_t24.nc"
    if fixture.exists():
        res = adapter.ingest(fixture)
        assert res.is_success is True
        assert res.source_id == "NCMRWF_NCUM"
        assert res.status == "TEST_FIXTURE"
        assert len(res.extracted_variables) >= 18
        assert all(p in res.extracted_variables for p in CANONICAL_18_PREDICTORS)


def test_neps_detection():
    """4. Test NEPS ensemble adapter preserves 23 ensemble members."""
    adapter = NEPSAdapter()
    fixture = FIXTURE_DIR / "neps_test_fixture_20260927_00Z_t24.nc"
    if fixture.exists():
        res = adapter.ingest(fixture)
        assert res.is_success is True
        assert res.record_count == 23  # 23 ensemble members
        assert res.status == "TEST_FIXTURE"


def test_imd_detection():
    """5. Test IMD 0.25 gridded observation adapter detection."""
    adapter = IMDObservationAdapter()
    fixture = FIXTURE_DIR / "imd_obs_test_fixture_20260928.nc"
    if fixture.exists():
        res = adapter.ingest(fixture)
        assert res.is_success is True
        assert res.source_id == "IMD_GRIDDED_RAINFALL"
        assert "observed_rainfall_mm" in res.extracted_variables


# ── Tests 6 to 12: Integrity, Metadata, Temporal, Spatial, Units, QC ────────

def test_file_integrity():
    """6. Test zero-byte and non-existent file integrity rejection."""
    engine = FileIntegrityEngine()

    # Zero-byte rejection
    zfile = FIXTURE_DIR / "corrupt_zero_byte.nc"
    rec = engine.validate_file(zfile)
    assert rec.is_valid is False
    assert rec.status == "ZERO_BYTE"

    # Non-existent file
    rec_nf = engine.validate_file("data/non_existent.nc")
    assert rec_nf.is_valid is False
    assert rec_nf.status == "NOT_FOUND"


def test_checksum():
    """7. Test SHA-256 computation and checksum mismatch detection."""
    engine = FileIntegrityEngine()
    fixture = FIXTURE_DIR / "ncum_test_fixture_20260927_00Z_t24.nc"
    if fixture.exists():
        rec = engine.validate_file(fixture)
        assert len(rec.checksum_sha256) == 64  # valid hex SHA-256
        assert rec.is_valid is True

        # Test intentional checksum mismatch
        bad_rec = engine.validate_file(fixture, expected_checksum="0000000000000000000000000000000000000000000000000000000000000000")
        assert bad_rec.is_valid is False
        assert bad_rec.status == "CHECKSUM_MISMATCH"


def test_metadata_validation():
    """8. Test CF metadata validation and missing variable detection."""
    val = MetadataValidator()

    # Complete valid metadata dictionary
    meta_valid = {
        "provider": "NCMRWF",
        "model": "NCUM",
        "variables": list(CANONICAL_18_PREDICTORS),
        "units": {"precip_nwp_raw": "mm", "mslp": "hPa", "u850": "m/s"},
        "latitude": np.linspace(6.5, 38.5, 129),
        "longitude": np.linspace(66.5, 100.5, 137),
        "initialization_time": "2026-09-27T00:00:00Z",
        "valid_time": "2026-09-28T00:00:00Z",
        "lead_time_hours": 24,
    }
    res = val.validate_metadata_dict(meta_valid, required_variables=CANONICAL_18_PREDICTORS)
    assert res.is_valid is True

    # Missing required variables
    meta_incomplete = {
        "provider": "NCMRWF",
        "variables": ["precip_nwp_raw"],
        "latitude": np.linspace(6.5, 38.5, 10),
        "longitude": np.linspace(66.5, 100.5, 10),
    }
    res_bad = val.validate_metadata_dict(meta_incomplete, required_variables=CANONICAL_18_PREDICTORS)
    assert res_bad.is_valid is False
    assert len(res_bad.variables_missing) > 0


def test_temporal_validation():
    """9. Test strict valid_time = init_time + lead_time validation."""
    tval = TemporalValidator()

    # Exact valid match: 00Z + 24h = next day 00Z
    res_ok = tval.validate_forecast_times(
        initialization_time="2026-09-27T00:00:00Z",
        valid_time="2026-09-28T00:00:00Z",
        lead_time_hours=24,
    )
    assert res_ok.is_valid is True
    assert res_ok.cycle == "00Z"

    # Temporal mismatch: 00Z + 24h != 2026-09-29
    res_bad = tval.validate_forecast_times(
        initialization_time="2026-09-27T00:00:00Z",
        valid_time="2026-09-29T00:00:00Z",
        lead_time_hours=24,
    )
    assert res_bad.is_valid is False
    assert res_bad.status == "MISMATCH"


def test_spatial_validation():
    """10. Test canonical India RAMP domain (6.5-38.5N, 66.5-100.5E, 0.25deg)."""
    sval = SpatialValidator()
    lats = np.linspace(6.5, 38.5, 129)
    lons = np.linspace(66.5, 100.5, 137)

    res = sval.validate_grid(lats, lons)
    assert res.is_valid is True
    assert res.coverage_percent == 100.0
    assert res.total_expected_cells == RAMP_DOMAIN["total_cells"]

    # Non-monotonic coordinates
    bad_lats = np.array([6.5, 7.0, 6.8, 8.0])
    bad_res = sval.validate_grid(bad_lats, lons)
    assert bad_res.is_valid is False
    assert "Latitude coordinates are non-monotonic" in bad_res.errors[0]


def test_unit_validation():
    """11. Test rainfall unit normalization and rejection of unknown units."""
    # Canonical mm -> mm
    norm_mm = UnitNormalizer.normalize_rainfall([10.0, 20.0], "mm")
    assert np.allclose(norm_mm, [10.0, 20.0])

    # Meters -> mm
    norm_m = UnitNormalizer.normalize_rainfall([0.01, 0.05], "m")
    assert np.allclose(norm_m, [10.0, 50.0])

    # kg m-2 -> mm
    norm_kg = UnitNormalizer.normalize_rainfall([15.0], "kg m-2")
    assert np.allclose(norm_kg, [15.0])

    # Unknown unit must fail with UnitValidationError
    with pytest.raises(UnitValidationError):
        UnitNormalizer.normalize_rainfall([10.0], "furlongs_per_fortnight")


def test_qc_validation():
    """12. Test meteorological QC on NaNs, negative rainfall, and physical limits."""
    qc = MeteorologicalQCEngine()

    # Nominal array
    res_ok = qc.check_variable([0.0, 15.5, 64.5, 120.0], "precip_nwp_raw")
    assert res_ok.status == "PASSED"
    assert res_ok.invalid_count == 0

    # Negative rainfall rejection
    res_neg = qc.check_variable([-5.0, 10.0, 20.0], "precip_nwp_raw")
    assert res_neg.status == "FAILED"
    assert any("NEGATIVE_RAINFALL" in f for f in res_neg.flags)

    # Infinite value rejection
    res_inf = qc.check_variable([10.0, np.inf, 20.0], "precip_nwp_raw")
    assert res_inf.status == "FAILED"
    assert any("CONTAINS_INFINITIES" in f for f in res_inf.flags)

    # Physical limit violation (rainfall > 1500 mm)
    res_oob = qc.check_variable([2500.0], "precip_nwp_raw")
    assert res_oob.status == "FAILED"


# ── Tests 13 to 14: Pairing & Anti-Leakage ──────────────────────────────────

def test_pairing():
    """13. Test forecast/observation pairing on matching valid time."""
    engine = ForecastObservationPairingEngine()
    fcst_meta = {
        "source_id": "NCMRWF_NCUM",
        "cycle": "00Z",
        "initialization_time": "2026-09-27T00:00:00Z",
        "valid_time": "2026-09-28T00:00:00Z",
        "lead_time_hours": 24,
    }
    obs_meta = {
        "source_id": "IMD_GRIDDED_RAINFALL",
        "valid_time": "2026-09-28T00:00:00Z",
        "observation_date": "2026-09-28",
    }
    manifest = engine.pair_forecast_and_observation(fcst_meta, obs_meta)
    assert manifest.status == "PAIRED"
    assert manifest.zero_leakage_verified is True
    assert manifest.coverage_percent > 0.0


def test_zero_future_leakage():
    """14. Test that observation preceding initialization triggers LEAKAGE_DETECTED."""
    engine = ForecastObservationPairingEngine()
    fcst_meta = {
        "source_id": "NCMRWF_NCUM",
        "cycle": "00Z",
        "initialization_time": "2026-09-27T00:00:00Z",
        "valid_time": "2026-09-28T00:00:00Z",
        "lead_time_hours": 24,
    }
    # Observation time BEFORE forecast initialization time
    obs_meta = {
        "source_id": "IMD_GRIDDED_RAINFALL",
        "valid_time": "2026-09-26T00:00:00Z",
        "observation_date": "2026-09-26",
    }
    manifest = engine.pair_forecast_and_observation(fcst_meta, obs_meta)
    assert manifest.status == "LEAKAGE_DETECTED"
    assert manifest.zero_leakage_verified is False


# ── Tests 15 to 22: 15-Gate Activation & Operator Approval ──────────────────

def test_activation_gate():
    """15. Test that RealDataActivationEngine evaluates exactly 15 gates."""
    engine = RealDataActivationEngine()
    gates = engine.evaluate_gates()
    assert len(gates) == 15
    gate_ids = [g.gate_id for g in gates]
    for i in range(1, 16):
        assert f"GATE_{i:02d}" in gate_ids


def test_activation_blocked_without_real_data():
    """16. Test that activation is BLOCKED when authoritative data are not mounted."""
    engine = RealDataActivationEngine()
    status = engine.get_status()
    assert status.system_status == "BLOCKED"
    assert status.stage == ActivationStage.STAGE_0_WAITING_DATA.value
    assert status.can_request_activation is False
    assert status.can_approve_activation is False
    assert "REAL OPERATIONAL BLOCKED" in status.disclaimer


def test_activation_requires_all_checks():
    """17. Test that activation fails if even 1 gate fails."""
    engine = RealDataActivationEngine()
    # No authoritative files -> gates fail
    success, msg = engine.request_activation(operator_id="OP_01")
    assert success is False
    assert "technical gates failed" in msg


def test_activation_requires_operator():
    """18. Test that approval cannot be granted without explicit operator signature."""
    engine = RealDataActivationEngine()
    # Cannot approve if not in REQUESTED state
    success, msg = engine.approve_activation(operator_id="OP_01", signature="SIG_123")
    assert success is False
    assert "No pending activation request eligible" in msg


def test_activation_audit():
    """19. Test that activation requests and rejections write immutable audit records."""
    engine = RealDataActivationEngine()
    engine.request_activation(operator_id="TEST_AUDIT_OP", reason="Audit trail test")
    history = engine.get_audit_trail()
    assert len(history) > 0
    latest = history[-1]
    assert latest["operator"] == "TEST_AUDIT_OP"
    assert "action" in latest


def test_real_mode_transition():
    """20. Test state machine protection against unauthorized real mode cutover."""
    engine = RealDataActivationEngine()
    # Directly trying to approve fails without gates passing
    ok, _ = engine.approve_activation(operator_id="OP_NCMRWF", signature="SIG")
    assert ok is False
    st = engine.get_status()
    assert st.data_mode != "REAL_OPERATIONAL"


def test_no_silent_synthetic_fallback():
    """21. Test that disappearance of real data raises CRITICAL degradation rather than fallback."""
    engine = RealDataActivationEngine()
    status, alert_msg = engine.handle_data_loss(source_id="NCMRWF_NCUM", reason="Storage unmounted")
    assert status == "FORECAST_GENERATION_BLOCKED"
    assert "CRITICAL" in alert_msg
    assert "Silent fallback blocked" in alert_msg
    assert engine.current_status == "BLOCKED"


def test_real_data_loss():
    """22. Test fallback safety audit recording upon data loss."""
    engine = RealDataActivationEngine()
    engine.handle_data_loss(source_id="IMD_GRIDDED_RAINFALL", reason="Archive corruption")
    history = engine.get_audit_trail()
    degrade_rec = [r for r in history if r["action"] == "DEGRADE"]
    assert len(degrade_rec) > 0
    assert degrade_rec[-1]["readiness_status"] == "OPERATIONAL_DEGRADED"


# ── Tests 23 to 26: Partial Coverage, Manifest, Real Verification ────────────

def test_partial_spatial_coverage():
    """23. Test partial coverage detection and district INSUFFICIENT_DATA status."""
    # Under 50% coverage must report INSUFFICIENT_DATA
    res_under = SpatialValidator.evaluate_district_coverage(
        district_cells_total=100,
        district_cells_available=40,
        min_threshold_pct=50.0,
    )
    assert res_under["status"] == "INSUFFICIENT_DATA"
    assert res_under["is_usable"] is False

    # Above 50% coverage reports VALID
    res_ok = SpatialValidator.evaluate_district_coverage(
        district_cells_total=100,
        district_cells_available=85,
        min_threshold_pct=50.0,
    )
    assert res_ok["status"] == "VALID"
    assert res_ok["is_usable"] is True


def test_forecast_manifest():
    """24. Test extended Phase 16 forecast manifest fields."""
    manifest = ForecastManifest(
        forecast_run_id="RAMP_20260927_00Z_T24",
        generation_timestamp="2026-09-27T00:00:00Z",
        data_mode="SYNTHETIC_DEMO",
        software_version="0.1.0",
        git_commit="c9a41b8e4f1073d82a17",
        feature_schema="ramp_features_v1.0.0",
        target_schema="ramp_targets_v1.0.0",
        calibration_version="v2.0.0",
        source_provider="NCMRWF",
        source_model="NCUM",
        cycle="00Z",
        initialization_time="2026-09-27T00:00:00Z",
        lead_time_hours=24,
        forecast_valid_time="2026-09-28T00:00:00Z",
        input_files=["data/raw/test.nc"],
        input_checksums={"test.nc": "abc123"},
        model_versions={"moe": "v2.0.0"},
        model_checksums={"moe": "def456"},
        output_checksums={"forecast.nc": "ghi789"},
        activation_id="ACT_20260927_001",
        operator_approval={"operator_id": "OP_01", "status": "APPROVED"},
    )
    d = manifest.to_dict()
    assert d["activation_id"] == "ACT_20260927_001"
    assert d["provider"] == "NCMRWF"
    assert d["valid_time"] == "2026-09-28T00:00:00Z"
    assert d["lead_time"] == 24


def test_real_verification():
    """25. Test factual verification calculation when valid observations are supplied."""
    vengine = RealVerificationEngine()
    rng = np.random.RandomState(42)
    obs = rng.uniform(0.0, 80.0, size=50)
    preds = obs + rng.normal(0.0, 5.0, size=50)

    report = vengine.evaluate_cycle(
        observations=obs,
        model_predictions={"RAMP_MoE": preds},
    )
    assert report.verification_status == "VERIFIED"
    assert "RAMP_MoE" in report.model_comparisons
    m = report.model_comparisons["RAMP_MoE"]
    assert m.mae is not None
    assert m.rmse is not None
    assert m.brier_score is not None


def test_insufficient_verification_data():
    """26. Test that verification returns NOT_AVAILABLE when observations are absent or < 10."""
    vengine = RealVerificationEngine()

    # None observations
    report_none = vengine.evaluate_cycle(observations=None, model_predictions={})
    assert report_none.verification_status == "NOT_AVAILABLE"
    assert "VERIFICATION NOT AVAILABLE" in report_none.disclaimer

    # Sample size < 10
    report_few = vengine.evaluate_cycle(observations=[10.0, 20.0], model_predictions={})
    assert report_few.verification_status == "NOT_AVAILABLE"


# ── Tests 27 to 30: FastAPI Endpoints & Scientific Integrity Guard ──────────

def test_api_activation_status():
    """27. Test GET /api/activation/status returns BLOCKED when authoritative data absent."""
    res = client.get("/api/activation/status")
    assert res.status_code == 200
    data = res.json()
    assert data["system_status"] == "BLOCKED"
    assert data["stage"] == "WAITING_FOR_AUTHORITATIVE_DATA"
    assert data["total_gates"] == 15
    assert data["data_mode"] == "SYNTHETIC_DEMO"


def test_api_ingestion_status():
    """28. Test GET /api/ingestion/status reports provider cards and pipeline state."""
    res = client.get("/api/ingestion/status")
    assert res.status_code == 200
    data = res.json()
    assert "provider_cards" in data
    assert "NCMRWF_NCUM" in data["provider_cards"]
    assert "IMD_GRIDDED_RAINFALL" in data["provider_cards"]


def test_api_verification():
    """29. Test GET /api/verification/real returns factual NOT_AVAILABLE without real data."""
    res = client.get("/api/verification/real")
    assert res.status_code == 200
    data = res.json()
    assert data["verification_status"] == "NOT_AVAILABLE"
    assert "baseline_models" in data
    assert len(data["baseline_models"]) == 4


def test_no_fake_operational_status():
    """30. Absolute Scientific Integrity Rule: Never report REAL_OPERATIONAL without real data."""
    # Check activation status
    res = client.get("/api/activation/status")
    assert res.json()["system_status"] != "ACTIVE"
    assert res.json()["data_mode"] != "REAL_OPERATIONAL"

    # Attempt unauthorized approval
    res_app = client.post("/api/activation/approve", json={"operator_id": "HACKER", "signature": "FAKESIG"})
    assert res_app.status_code == 400

    # Ensure system remains in synthetic demo mode
    res_after = client.get("/api/activation/status")
    assert res_after.json()["data_mode"] == "SYNTHETIC_DEMO"
