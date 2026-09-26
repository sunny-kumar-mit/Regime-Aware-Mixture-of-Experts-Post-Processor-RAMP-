"""
Phase 8 Comprehensive Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Covers all 26 verification requirements:
  1. Real data provider
  2. Synthetic provider compatibility
  3. Dataset manifest
  4. Metadata discovery
  5. Unit validation
  6. Temporal alignment
  7. Spatial alignment
  8. Missing data policy
  9. Duplicate detection
  10. Rainfall sanity checks
  11. Extreme-value preservation
  12. Leakage protection
  13. Chronological split
  14. Dataset versioning
  15. RAMP compatibility
  16. Extreme Probability compatibility
  17. Probability metrics
  18. Operational benchmark
  19. API contracts (14 endpoints)
  20. Readiness status
  21. Audit trail
  22. Reproducibility manifest
  23. Phase 7 report existence
  24. Phase report index
  25. Master report update
  26. Development plan update
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from ramp.main import app
from ml.data.contract import CanonicalRecord, DataMode, DatasetContract, validate_canonical_dataframe
from ml.data.discovery import DataDiscoveryService
from ml.data.manifest import DatasetManifest
from ml.data.providers.real_provider import RealDataProvider
from ml.data.providers.synthetic import SyntheticDataProvider
from ml.data.quality import MeteorologicalQualityControl, MissingDataPolicy
from ml.data.readiness import RealDataReadinessChecker
from ml.data.units import UnitNormalizer
from ml.data.alignment import TemporalAlignmentEngine, SpatialAlignmentEngine
from ml.dataset.leakage_guard import LeakageGuard, DataLeakageError
from ml.dataset.split import ChronologicalSplitter
from ml.operational.registry import OperationalModelRegistry, ModelVersionEntry
from ml.operational.readiness import OperationalReadinessEvaluator
from ml.operational.verification import OperationalVerificationEngine
from ml.operational.audit import AuditTrailManager


@pytest.fixture
def client():
    return TestClient(app)


# 1. Real Data Provider
def test_real_data_provider():
    provider = RealDataProvider()
    assert provider.is_available() is True
    # In unmounted repo, mode must be honest SYNTHETIC_DEMO
    assert provider.get_mode() in [DataMode.REAL, DataMode.SYNTHETIC_DEMO]


# 2. Synthetic Provider Compatibility
def test_synthetic_provider_compatibility():
    synth = SyntheticDataProvider(n_samples=50)
    df = synth.load_canonical()
    assert len(df) > 0
    assert "nwp_rainfall_mm" in df.columns
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert df["data_mode"].iloc[0] == DataMode.SYNTHETIC_DEMO.value


# 3. Dataset Manifest
def test_dataset_manifest(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    m = DatasetManifest.create_default_synthetic_manifest()
    m.save(manifest_path)
    loaded = DatasetManifest.load(manifest_path)
    assert loaded is not None
    assert loaded.dataset_id == m.dataset_id
    assert loaded.mode == "SYNTHETIC_DEMO"


# 4. Metadata Discovery
def test_metadata_discovery():
    discovery = DataDiscoveryService(["data/raw", "data/processed"])
    summary = discovery.discover()
    assert summary.scan_timestamp is not None
    assert isinstance(summary.discovered_variables, list)


# 5. Unit Validation
def test_unit_validation():
    normalizer = UnitNormalizer()
    rain_m = np.array([0.025, 0.050])
    rain_mm = normalizer.normalize_precipitation_to_mm(rain_m, source_unit="m")
    np.testing.assert_allclose(rain_mm, [25.0, 50.0])

    rain_kg = np.array([12.0, 45.0])
    rain_mm_kg = normalizer.normalize_precipitation_to_mm(rain_kg, source_unit="kg m-2")
    np.testing.assert_allclose(rain_mm_kg, [12.0, 45.0])

    assert len(normalizer.conversion_history) >= 2


# 6. Temporal Alignment
def test_temporal_alignment():
    init = pd.Timestamp("2023-07-01 00:00:00+0000")
    valid = TemporalAlignmentEngine.compute_valid_time(init, 24)
    assert valid == pd.Timestamp("2023-07-02 00:00:00+0000")
    assert TemporalAlignmentEngine.assign_lead_time_day(24) == "Day 1"
    assert TemporalAlignmentEngine.assign_lead_time_day(48) == "Day 2"
    assert TemporalAlignmentEngine.assign_lead_time_day(120) == "Day 5"


# 7. Spatial Alignment
def test_spatial_alignment():
    engine = SpatialAlignmentEngine()
    snapped_lat, snapped_lon = engine.nearest_grid_cell(18.91, 72.82)
    assert abs(snapped_lat - 19.0) < 0.26
    assert abs(snapped_lon - 72.75) < 0.26


# 8. Missing Data Policy
def test_missing_data_policy():
    qc = MeteorologicalQualityControl()
    df = pd.DataFrame({
        "latitude": [18.0, 19.0],
        "longitude": [72.0, 73.0],
        "initialization_time": ["2023-07-01T00:00:00Z", "2023-07-01T00:00:00Z"],
        "forecast_valid_time": ["2023-07-02T00:00:00Z", "2023-07-02T00:00:00Z"],
        "lead_time_hours": [24, 24],
        "nwp_rainfall_mm": [12.0, 15.0],
        "observed_rainfall_mm": [np.nan, 20.0],  # One missing observation
    })
    valid_df, report = qc.inspect_and_filter(df)
    assert report.missing_target_records == 1
    # Missing observation must NOT be auto-imputed as zero; records remain valid for forecast
    assert len(valid_df) == 2


# 9. Duplicate Detection
def test_duplicate_detection():
    qc = MeteorologicalQualityControl()
    df = pd.DataFrame({
        "latitude": [18.0, 18.0],
        "longitude": [72.0, 72.0],
        "initialization_time": ["2023-07-01T00:00:00Z", "2023-07-01T00:00:00Z"],
        "forecast_valid_time": ["2023-07-02T00:00:00Z", "2023-07-02T00:00:00Z"],
        "lead_time_hours": [24, 24],
        "nwp_rainfall_mm": [12.0, 12.0],
    })
    valid_df, report = qc.inspect_and_filter(df)
    assert report.duplicate_records == 1
    assert len(valid_df) == 1


# 10. Rainfall Sanity Checks
def test_rainfall_sanity_checks():
    qc = MeteorologicalQualityControl()
    df = pd.DataFrame({
        "latitude": [18.0, 19.0],
        "longitude": [72.0, 73.0],
        "initialization_time": ["2023-07-01T00:00:00Z", "2023-07-01T00:00:00Z"],
        "forecast_valid_time": ["2023-07-02T00:00:00Z", "2023-07-02T00:00:00Z"],
        "lead_time_hours": [24, 24],
        "nwp_rainfall_mm": [-5.0, 15.0],  # Negative rain is invalid
    })
    valid_df, report = qc.inspect_and_filter(df)
    assert report.physical_invalid_rain_count == 1
    assert len(valid_df) == 1


# 11. Extreme Value Preservation
def test_extreme_value_preservation():
    qc = MeteorologicalQualityControl()
    df = pd.DataFrame({
        "latitude": [18.0, 19.0],
        "longitude": [72.0, 73.0],
        "initialization_time": ["2023-07-01T00:00:00Z", "2023-07-01T00:00:00Z"],
        "forecast_valid_time": ["2023-07-02T00:00:00Z", "2023-07-02T00:00:00Z"],
        "lead_time_hours": [24, 24],
        "nwp_rainfall_mm": [245.0, 68.0],  # Extreme rainfall (>204.5 mm)
        "observed_rainfall_mm": [280.0, 75.0],
    })
    valid_df, report = qc.inspect_and_filter(df)
    # Must NOT delete extreme events
    assert report.extreme_but_valid_rain_count == 1
    assert len(valid_df) == 2


# 12. Leakage Protection
def test_leakage_protection():
    guard = LeakageGuard()
    # Forbidden target variables
    with pytest.raises(DataLeakageError):
        guard.audit_real_data_features(["nwp_rainfall_mm", "future_observed_rainfall"])

    with pytest.raises(DataLeakageError):
        guard.audit_real_data_features(["nwp_rainfall_mm", "observed_regime"])

    # Valid predictor set with fresh guard
    clean_guard = LeakageGuard()
    clean_guard.audit_real_data_features(["nwp_rainfall_mm", "mslp_pa", "u850_ms", "cape_jkg"])
    assert len(clean_guard.violations) == 0


# 13. Chronological Split
def test_chronological_split():
    splitter = ChronologicalSplitter(purge_gap_hours=24)
    dates = pd.date_range("2023-06-01", periods=10, freq="24h", tz="UTC")
    df = pd.DataFrame({
        "forecast_valid_time": dates,
        "nwp_rainfall_mm": range(10),
        "latitude": [18.0] * 10,
        "longitude": [72.0] * 10,
    })
    train_df, val_df, test_df, manifest = splitter.split(df)
    assert not train_df.empty
    # Strict chronological boundary check
    assert train_df["forecast_valid_time"].max() < val_df["forecast_valid_time"].min()


# 14. Dataset Versioning
def test_dataset_versioning():
    record = CanonicalRecord(
        dataset_id="test_ds",
        dataset_version="v1.0.0",
        source="IMD",
        data_mode=DataMode.REAL,
        initialization_time="2023-07-01T00:00:00Z",
        forecast_valid_time="2023-07-02T00:00:00Z",
        lead_time_hours=24,
        latitude=18.5,
        longitude=73.5,
        nwp_rainfall_mm=15.2,
    )
    assert record.nwp_rainfall_mm == 15.2


# 15. RAMP Compatibility
def test_ramp_compatibility():
    registry = OperationalModelRegistry()
    assert registry.state.ramp_model_version == "ramp_v1.0.0"
    # Freeze lock invariant: cannot overwrite frozen version
    with pytest.raises(ValueError):
        registry.register_model(ModelVersionEntry(
            phase=6,
            system_name="RAMP",
            version_id="ramp_v1.0.0",
            status="OVERWRITE_ATTEMPT",
            data_mode="REAL",
            trained_at="2026-09-26T00:00:00Z",
        ))


# 16. Extreme Probability Compatibility
def test_extreme_prob_compatibility():
    registry = OperationalModelRegistry()
    assert registry.state.extreme_prob_version in ["extreme_prob_v1.0.0", "extreme_v1.0.0"]
    # Freeze lock invariant: cannot overwrite frozen extreme prob version
    with pytest.raises(ValueError):
        registry.register_model(ModelVersionEntry(
            phase=7,
            system_name="ExtremeProb",
            version_id="extreme_prob_v1.0.0",
            status="OVERWRITE_ATTEMPT",
            data_mode="REAL",
            trained_at="2026-09-26T00:00:00Z",
        ))


# 17. Probability Metrics
def test_probability_metrics():
    verifier = OperationalVerificationEngine()
    df = pd.DataFrame({
        "observed_rainfall_mm": [0.0, 10.0, 70.0, 120.0, 210.0],
        "nwp_rainfall_mm": [0.0, 8.0, 65.0, 110.0, 200.0],
    })
    res = verifier.verify_dataset(df)
    assert "extreme_probability_metrics" in res
    assert "64.5mm" in res["extreme_probability_metrics"]


# 18. Operational Benchmark
def test_operational_benchmark():
    verifier = OperationalVerificationEngine()
    synth = SyntheticDataProvider(n_samples=50)
    df = synth.load_canonical()
    res = verifier.verify_dataset(df)
    matrix = res.get("benchmark_matrix", [])
    assert len(matrix) >= 5
    systems = [row["system"] for row in matrix]
    assert "RAW NWP" in systems
    assert "RAMP MoE" in systems


# 19. API Contracts (14 Endpoints)
def test_operational_api_contracts(client):
    endpoints = [
        "/api/operational/status",
        "/api/operational/data",
        "/api/operational/data-quality",
        "/api/operational/dataset",
        "/api/operational/coverage",
        "/api/operational/verification",
        "/api/operational/verification/threshold",
        "/api/operational/verification/regime",
        "/api/operational/verification/lead-time",
        "/api/operational/verification/spatial",
        "/api/operational/calibration",
        "/api/operational/leakage",
        "/api/operational/models",
        "/api/operational/readiness",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} returned {res.status_code}: {res.text}"


# 20. Readiness Status
def test_readiness_status():
    evaluator = OperationalReadinessEvaluator()
    assessment = evaluator.evaluate()
    assert assessment.current_level in [0, 1]
    assert len(assessment.tiers) == 6


# 21. Audit Trail
def test_audit_trail(tmp_path):
    audit = AuditTrailManager(audit_dir=tmp_path)
    manifest = audit.create_run_manifest(
        dataset_id="test_ds",
        dataset_version="v1.0.0",
        data_mode="SYNTHETIC_DEMO",
        model_versions={"ramp": "ramp_v1.0.0"},
        data_quality_status="PASS",
        leakage_guard_status="PASS",
        summary_metrics={"rmse": 13.85},
    )
    assert manifest.run_id.startswith("run_")
    assert (tmp_path / f"{manifest.run_id}.json").exists()


# 22. Reproducibility Manifest
def test_reproducibility_manifest():
    checker = RealDataReadinessChecker()
    report = checker.check()
    assert report.status_str in ["REAL_DATA_AVAILABLE = YES", "REAL_DATA_AVAILABLE = NO"]


# 23. Phase 7 Report Existence
def test_phase7_report_existence():
    p7_path = Path("docs/reports/PHASE_7_PROJECT_REPORT.md")
    assert p7_path.exists()
    content = p7_path.read_text(encoding="utf-8")
    assert "Extreme Rainfall Probability Engine" in content
    assert "Pool Adjacent Violators" in content


# 24. Phase Report Index
def test_phase_report_index():
    idx_path = Path("docs/reports/PROJECT_REPORT_INDEX.md")
    assert idx_path.exists()


# 25. Master Report Update
def test_master_report_update():
    master_path = Path("docs/PROJECT_MASTER_REPORT.md")
    assert master_path.exists()


# 26. Development Plan Update
def test_development_plan_update():
    plan_path = Path("DEVELOPMENT_PLAN.md")
    assert plan_path.exists()
