"""
Phase 18 — Real-Data Activation, Institutional Acceptance Testing & Scientific Verification Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

PART AQ — Mandatory Minimum Test Coverage (35 Tests):
  1.  test_authoritative_source_detection
  2.  test_unmounted_data_block
  3.  test_ncum_real_schema
  4.  test_neps_member_validation
  5.  test_imd_real_schema
  6.  test_multi_cycle_discovery
  7.  test_checksum_validation
  8.  test_metadata_validation
  9.  test_temporal_alignment
  10. test_spatial_alignment
  11. test_unit_validation
  12. test_meteorological_qc
  13. test_pairing_zero_leakage
  14. test_real_inference
  15. test_probability_monotonicity
  16. test_forecast_provenance
  17. test_real_verification
  18. test_sample_sufficiency
  19. test_baseline_comparison
  20. test_multi_lead_verification
  21. test_threshold_verification
  22. test_regime_verification
  23. test_spatial_verification
  24. test_fss
  25. test_calibration
  26. test_case_replay
  27. test_acceptance_status
  28. test_staging_mode
  29. test_cutover_authorization
  30. test_supervisor_approval
  31. test_no_fake_real_status
  32. test_no_fake_verification
  33. test_no_model_retraining
  34. test_real_data_loss
  35. test_audit_completeness
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

from ml.acceptance.sources import (
    AuthoritativeMountValidator,
    MountClassification,
    AuthorityLevel,
)
from ml.acceptance.validation import (
    NCUMValidator,
    NEPSValidator,
    IMDValidator,
    RealDataIntegrityMatrix,
)
from ml.acceptance.cycles import MultiCycleDiscoveryEngine
from ml.acceptance.staging import StagingRealDataEngine
from ml.acceptance.verification import (
    ScientificVerificationEngine,
    BaselineComparisonEngine,
    MultiLeadVerificationEngine,
    ThresholdVerificationEngine,
    RegimeStratifiedVerificationEngine,
    SpatialVerificationEngine,
    FSSVerificationEngine,
    CalibrationAnalysisEngine,
    DailyOperationalVerificationReporter,
)
from ml.acceptance.cases import OperationalCaseReplayService, FailureAnalysisEngine
from ml.acceptance.engine import InstitutionalAcceptanceEngine, AcceptanceVerdict, CheckStatus
from ml.ingestion.pairing import ForecastObservationPairingEngine

from ramp.main import app

client = TestClient(app)
FIXTURE_DIR = Path("tests/fixtures/phase18")


# ── Tests 1 to 5: Source Detection & Schemas ──────────────────────────────

def test_authoritative_source_detection():
    """1. Test detection of authoritative primary sources."""
    validator = AuthoritativeMountValidator()
    report = validator.audit_all_sources()
    assert report["authoritative_primary_sources_count"] == 3
    sources = report["sources"]
    source_ids = {s["source_id"] for s in sources}
    assert "NCMRWF_NCUM" in source_ids
    assert "NCMRWF_NEPS" in source_ids
    assert "IMD_GRIDDED_RAINFALL" in source_ids


def test_unmounted_data_block():
    """2. Test that unmounted operational data correctly blocks REAL_OPERATIONAL activation."""
    validator = AuthoritativeMountValidator()
    report = validator.audit_all_sources()
    # In unmounted baseline, real operational is blocked
    assert report["real_operational_blocked"] is True
    assert report["overall_status"] in ["WAITING_FOR_AUTHORITATIVE_DATA", "AUTHORITATIVE_DATA_PARTIAL"]


def test_ncum_real_schema():
    """3. Test NCUM 18-predictor schema validation and rejection of missing predictors."""
    v = NCUMValidator()
    valid_file = FIXTURE_DIR / "ncum_valid_test_fixture.nc"
    inv_file = FIXTURE_DIR / "ncum_invalid_missing_predictors.nc"

    valid_rep = v.validate_file(valid_file)
    assert valid_rep.all_18_predictors_present is True
    assert valid_rep.status == "PASS"

    inv_rep = v.validate_file(inv_file)
    assert inv_rep.all_18_predictors_present is False
    assert inv_rep.status == "INVALID"
    assert len(inv_rep.missing_variables) > 0


def test_neps_member_validation():
    """4. Test NEPS 23-member ensemble validation and exact reporting of missing members."""
    v = NEPSValidator()
    valid_file = FIXTURE_DIR / "neps_valid_23_members.nc"
    miss_file = FIXTURE_DIR / "neps_missing_members.nc"

    v_rep = v.validate_file(valid_file)
    assert v_rep.total_members_found == 23
    assert len(v_rep.missing_members) == 0
    assert v_rep.status == "PASS"

    m_rep = v.validate_file(miss_file)
    assert m_rep.total_members_found == 20
    assert len(m_rep.missing_members) == 3
    assert "ens20" in m_rep.missing_members
    assert "ens21" in m_rep.missing_members
    assert "ens22" in m_rep.missing_members
    assert m_rep.status == "INCOMPLETE"


def test_imd_real_schema():
    """5. Test IMD 0.25° grid schema and strict ground-truth isolation invariant."""
    v = IMDValidator()
    valid_file = FIXTURE_DIR / "imd_valid_025_grid.nc"
    inv_file = FIXTURE_DIR / "imd_invalid_negative_rain.nc"

    v_rep = v.validate_file(valid_file)
    assert v_rep.status == "PASS"
    assert v_rep.is_ground_truth_isolated is True
    assert v_rep.coverage_percent > 90.0

    i_rep = v.validate_file(inv_file)
    assert i_rep.status == "INVALID"
    assert i_rep.qc_passed is False


# ── Tests 6 to 13: Integrity, Alignment, Pairing & QC ──────────────────────

def test_multi_cycle_discovery():
    """6. Test multi-cycle discovery logic and SAMPLE_LIMITED labeling."""
    engine = MultiCycleDiscoveryEngine(search_roots=[FIXTURE_DIR])
    rep = engine.discover_cycles()
    assert rep.total_cycles_discovered >= 1
    # When sample count < 3 cycles, must label SAMPLE_LIMITED
    if rep.total_cycles_discovered < 3:
        assert rep.status_label == "SAMPLE_LIMITED"
        assert rep.acceptance_threshold_met is False


def test_checksum_validation():
    """7. Test cryptographic SHA-256 checksum computation."""
    fpath = FIXTURE_DIR / "ncum_valid_test_fixture.nc"
    chk1 = NCUMValidator.compute_sha256(fpath)
    chk2 = NCUMValidator.compute_sha256(fpath)
    assert len(chk1) == 64
    assert chk1 == chk2


def test_metadata_validation():
    """8. Test CF and GRIB metadata coordinate checks."""
    v = NCUMValidator()
    rep = v.validate_file(FIXTURE_DIR / "ncum_valid_test_fixture.nc")
    assert rep.spatial_extent_valid is True
    check_names = [c.check_name for c in rep.checks]
    assert "spatial_domain" in check_names


def test_temporal_alignment():
    """9. Test temporal consistency: valid_time = init_time + lead_time."""
    v = NCUMValidator()
    rep = v.validate_file(FIXTURE_DIR / "ncum_valid_test_fixture.nc")
    assert rep.temporal_alignment_valid is True
    assert rep.lead_time_hours == 24


def test_spatial_alignment():
    """10. Test rejection of non-canonical spatial bounds."""
    v = NCUMValidator()
    bad_coords = FIXTURE_DIR / "ncum_bad_coordinates.nc"
    rep = v.validate_file(bad_coords)
    assert rep.spatial_extent_valid is False
    assert rep.status == "INVALID"


def test_unit_validation():
    """11. Test canonical precipitation units validation."""
    v = NCUMValidator()
    rep = v.validate_file(FIXTURE_DIR / "ncum_valid_test_fixture.nc")
    assert rep.unit_consistency_valid is True


def test_meteorological_qc():
    """12. Test meteorological QC and rejection of unphysical negative rainfall."""
    v = IMDValidator()
    inv_file = FIXTURE_DIR / "imd_invalid_negative_rain.nc"
    rep = v.validate_file(inv_file)
    assert rep.qc_passed is False
    assert any("negative" in f.failure_reason.lower() for f in rep.failures)


def test_pairing_zero_leakage():
    """13. Test pairing engine anti-leakage guarantee."""
    engine = ForecastObservationPairingEngine()
    # Observation before forecast init must trigger LEAKAGE_DETECTED
    fcst_meta = {
        "cycle": "00Z",
        "initialization_time": "2026-09-27T00:00:00Z",
        "valid_time": "2026-09-28T00:00:00Z",
        "lead_time_hours": 24,
    }
    obs_meta_leaked = {
        "valid_time": "2026-09-26T00:00:00Z",  # Before initialization!
    }
    manifest = engine.pair_forecast_and_observation(fcst_meta, obs_meta_leaked)
    assert manifest.status == "LEAKAGE_DETECTED"
    assert manifest.zero_leakage_verified is False


# ── Tests 14 to 20: Staging, Monotonicity, Verification & Baselines ────────

def test_real_inference():
    """14. Test that real inference runs with frozen model artifacts."""
    engine = StagingRealDataEngine()
    valid_ncum = FIXTURE_DIR / "ncum_valid_test_fixture.nc"
    verdict = engine.execute_staging_cycle(
        cycle_id="20260927_00Z",
        lead_hours=24,
        ncum_file=valid_ncum,
    )
    assert verdict.model_provenance_valid is True
    assert verdict.data_mode == "STAGING_REAL_DATA"


def test_probability_monotonicity():
    """15. Test probability monotonicity constraint: P(>=2.5) >= P(>=15.6) >= P(>=64.5) >= P(>=115.6) >= P(>=204.5)."""
    # Valid monotonicity
    valid_probs = {"p_ge_2_5": 0.85, "p_ge_15_6": 0.55, "p_ge_64_5": 0.25, "p_ge_115_6": 0.08, "p_ge_204_5": 0.01}
    res_valid = StagingRealDataEngine.validate_probability_monotonicity(valid_probs)
    assert res_valid.is_valid is True
    assert len(res_valid.violations) == 0

    # Inverted monotonicity violation
    inv_probs = {"p_ge_2_5": 0.40, "p_ge_15_6": 0.70, "p_ge_64_5": 0.10, "p_ge_115_6": 0.05, "p_ge_204_5": 0.01}
    res_inv = StagingRealDataEngine.validate_probability_monotonicity(inv_probs)
    assert res_inv.is_valid is False
    assert len(res_inv.violations) > 0


def test_forecast_provenance():
    """16. Test that staging execution produces complete cryptographic provenance manifest."""
    engine = StagingRealDataEngine()
    valid_ncum = FIXTURE_DIR / "ncum_valid_test_fixture.nc"
    verdict = engine.execute_staging_cycle(cycle_id="20260927_00Z", lead_hours=24, ncum_file=valid_ncum)
    assert verdict.manifest is not None
    m = verdict.manifest
    assert "forecast_id" in m
    assert "git_commit" in m
    assert "model_version" in m
    assert "output_checksum" in m


def test_real_verification():
    """17. Test scientific continuous and categorical metric calculation."""
    obs = np.array([5.0, 12.0, 45.0, 70.0, 85.0, 110.0, 15.0, 2.0, 0.0, 30.0, 18.0, 22.0])
    pred = np.array([4.0, 10.0, 40.0, 68.0, 80.0, 115.0, 18.0, 1.0, 0.5, 28.0, 19.0, 20.0])

    cont = ScientificVerificationEngine.calculate_continuous(obs, pred)
    assert cont is not None
    assert cont.rmse > 0.0
    assert cont.pearson_correlation > 0.9

    cat = ScientificVerificationEngine.calculate_categorical(obs, pred, 64.5)
    assert cat is not None
    assert 0.0 <= cat.csi <= 1.0


def test_sample_sufficiency():
    """18. Test that verification returns None or NOT_AVAILABLE when sample count < 10."""
    obs_small = np.array([5.0, 12.0, 45.0])
    pred_small = np.array([4.0, 10.0, 40.0])
    cont = ScientificVerificationEngine.calculate_continuous(obs_small, pred_small)
    assert cont is None

    res = BaselineComparisonEngine.build_comparison_table(obs_small, {"RAMP": pred_small})
    assert res["status"] == "NOT_AVAILABLE"


def test_baseline_comparison():
    """19. Test baseline comparison table: factual measurements only, NO winner or rank labels."""
    obs = np.random.uniform(0.0, 80.0, 50)
    preds = {
        "RAMP": np.random.uniform(0.0, 80.0, 50),
        "Raw_NCUM": np.random.uniform(0.0, 80.0, 50),
        "NEPS_Mean": np.random.uniform(0.0, 80.0, 50),
        "Persistence": np.random.uniform(0.0, 80.0, 50),
        "Climatology": np.ones(50) * 12.5,
    }
    table_res = BaselineComparisonEngine.build_comparison_table(obs, preds)
    assert table_res["status"] == "MEASURED"
    assert len(table_res["table"]) == 5
    for row in table_res["table"]:
        # Verify no evaluative ranking fields
        assert "rank" not in row
        assert "is_winner" not in row
        assert "score" not in row


def test_multi_lead_verification():
    """20. Test multi-lead evaluation and insufficient sample handling."""
    paired_cycles = [
        {"lead_hours": 24, "has_observation": True} for _ in range(15)
    ]
    res = MultiLeadVerificationEngine.evaluate_leads(paired_cycles)
    assert res["leads"]["+24h"]["status"] == "MEASURED"
    assert res["leads"]["+72h"]["status"] == "NOT_AVAILABLE"


# ── Tests 21 to 26: Thresholds, Regimes, Spatial, FSS & Replay ─────────────

def test_threshold_verification():
    """21. Test multi-threshold evaluation across 2.5, 15.6, 64.5, 115.6, 204.5 mm."""
    obs = np.random.uniform(0.0, 150.0, 40)
    pred = np.random.uniform(0.0, 150.0, 40)
    res = ThresholdVerificationEngine.evaluate_thresholds(obs, pred)
    assert res["status"] == "MEASURED"
    assert "2.5" in res["thresholds"]
    assert "64.5" in res["thresholds"]
    assert "204.5" in res["thresholds"]


def test_regime_verification():
    """22. Test regime-stratified verification and SAMPLE_LIMITED labeling."""
    samples = [{"regime": "active_monsoon"} for _ in range(12)] + [{"regime": "break_monsoon"} for _ in range(3)]
    res = RegimeStratifiedVerificationEngine.evaluate_regimes(samples)
    assert res["regimes"]["active_monsoon"]["status"] == "MEASURED"
    assert res["regimes"]["break_monsoon"]["status"] == "SAMPLE_LIMITED"


def test_spatial_verification():
    """23. Test spatial verification across grid, district, state, and national tiers."""
    # When real data unmounted:
    res_unmounted = SpatialVerificationEngine.evaluate_spatial_tiers(has_real_data=False)
    assert res_unmounted["status"] == "NOT_AVAILABLE"

    # When real data available:
    res_mounted = SpatialVerificationEngine.evaluate_spatial_tiers(has_real_data=True)
    assert res_mounted["status"] == "MEASURED"
    assert "district" in res_mounted["tiers"]
    assert "state" in res_mounted["tiers"]


def test_fss():
    """24. Test Fractions Skill Score evaluation and NOT_AVAILABLE guard."""
    fss_unmounted = FSSVerificationEngine.evaluate_fss(has_real_data=False)
    assert fss_unmounted["status"] == "NOT_AVAILABLE"

    fss_mounted = FSSVerificationEngine.evaluate_fss(has_real_data=True)
    assert fss_mounted["status"] == "MEASURED"
    assert "25km" in fss_mounted["matrix"]
    assert "64.5mm" in fss_mounted["matrix"]["25km"]


def test_calibration():
    """25. Test probabilistic calibration curves and sharpness analysis."""
    cal_unmounted = CalibrationAnalysisEngine.evaluate_calibration(has_real_data=False)
    assert cal_unmounted["status"] == "CALIBRATION_NOT_AVAILABLE"

    cal_mounted = CalibrationAnalysisEngine.evaluate_calibration(has_real_data=True)
    assert cal_mounted["status"] == "MEASURED"
    assert len(cal_mounted["reliability_curve"]) == 10
    assert cal_mounted["expected_calibration_error"] is not None


def test_case_replay():
    """26. Test operational case study replay service."""
    service = OperationalCaseReplayService()
    cases = service.list_cases()
    # When no real cycles cataloged, returns honest report
    assert cases["status"] == "NO_REAL_CASE_STUDIES_AVAILABLE"
    assert cases["cases_count"] == 0


# ── Tests 27 to 35: Governance, Cutover, Safety & Audit ─────────────────────

def test_acceptance_status():
    """27. Test institutional acceptance scorecard API and overall verdict."""
    response = client.get("/api/acceptance/status")
    assert response.status_code == 200
    data = response.json()
    assert "overall_verdict" in data
    assert "category_verdicts" in data
    assert len(data["category_verdicts"]) == 12
    # In unmounted baseline, status must be BLOCKED
    assert data["overall_verdict"] == "BLOCKED"
    assert data["real_operational_launch"] is False


def test_staging_mode():
    """28. Test staging execution API: publication strictly disabled."""
    valid_ncum = str(FIXTURE_DIR / "ncum_valid_test_fixture.nc")
    resp = client.post(
        "/api/acceptance/staging-run",
        json={"cycle_id": "20260927_00Z", "lead_hours": 24, "ncum_file": valid_ncum},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PASS"
    assert data["publication_allowed"] is False
    assert data["data_mode"] == "STAGING_REAL_DATA"


def test_cutover_authorization():
    """29. Test that cutover request is rejected when authoritative data are unmounted."""
    resp = client.post(
        "/api/acceptance/request-activation",
        json={"operator_id": "OPERATOR_NCMRWF_01", "reason": "Operational Monsoon Run"},
    )
    # Unmounted -> rejected with 400
    assert resp.status_code == 400
    assert "unmounted" in resp.json()["detail"].lower()


def test_supervisor_approval():
    """30. Test two-stage cutover: supervisor approval requires valid preceding operator request."""
    engine = InstitutionalAcceptanceEngine()
    # Attempting approval without prior request must fail
    success, msg = engine.approve_activation("SUPERVISOR_01", "PIN1234", has_authoritative_mount=True)
    assert success is False
    assert "preceded by a formal operator request" in msg


def test_no_fake_real_status():
    """31. Test that system never reports fake REAL_OPERATIONAL_ACTIVE when data unmounted."""
    engine = InstitutionalAcceptanceEngine()
    scorecard = engine.evaluate_acceptance(has_authoritative_mount=False)
    assert scorecard.overall_verdict == "BLOCKED"
    assert scorecard.real_operational_launch is False


def test_no_fake_verification():
    """32. Test that verification API returns NOT_AVAILABLE when data unmounted."""
    resp = client.get("/api/acceptance/verification")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NOT_AVAILABLE"
    assert "not mounted" in data["disclaimer"].lower() or "unmounted" in data["disclaimer"].lower()


def test_no_model_retraining():
    """33. Test model immutability: models remain strictly frozen and registry is intact."""
    resp = client.get("/api/acceptance/inference")
    assert resp.status_code == 200
    data = resp.json()
    assert "ramp_moe_v2.0.0" in data["frozen_models"]["REGIME_AWARE_MOE"]
    assert "LOCKED" in data["immutability_status"]


def test_real_data_loss():
    """34. Test safety handling when real data stream is lost."""
    from ml.ingestion.activation import RealDataActivationEngine
    engine = RealDataActivationEngine()
    status, alert = engine.handle_data_loss("NCMRWF_NCUM", "Stream severed")
    assert status == "FORECAST_GENERATION_BLOCKED"
    assert "OPERATIONAL_DEGRADED" in alert
    assert "Silent fallback blocked" in alert


def test_audit_completeness():
    """35. Test completeness of institutional acceptance audit trail and incident correlation."""
    engine = InstitutionalAcceptanceEngine()
    inc = engine.create_incident("20260927_00Z", "CRITICAL", "Corrupt file detected")
    assert inc.incident_id.startswith("INC_")
    incidents = engine.list_incidents()
    assert len(incidents) >= 1
    assert any(i["incident_id"] == inc.incident_id for i in incidents)
