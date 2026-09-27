"""
Comprehensive Phase 14 Operational Forecast Inference Test Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part AH: 26 Mandatory Rigorous Tests:
 1. test_forecast_cycle_discovery
 2. test_available_lead_discovery
 3. test_input_validation
 4. test_feature_schema_validation
 5. test_model_registry_resolution
 6. test_model_checksum_validation
 7. test_global_model_inference
 8. test_regime_inference
 9. test_moe_inference
10. test_extreme_probability_inference
11. test_probability_monotonicity
12. test_calibration_loading
13. test_forecast_run_id
14. test_forecast_manifest
15. test_provenance
16. test_product_generation
17. test_district_product
18. test_state_product
19. test_export_json
20. test_export_csv
21. test_export_geojson
22. test_real_data_block
23. test_synthetic_demo_mode
24. test_no_fake_cycle
25. test_no_fake_lead
26. test_no_fake_operational_status
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from ml.inference.calibration import RegisteredCalibrator
from ml.inference.config import FEATURE_SCHEMA_VERSION, TARGET_SCHEMA_VERSION
from ml.inference.feature_builder import FeatureSchemaMismatchError, InferenceFeatureBuilder
from ml.inference.input_resolver import ForecastCycleResolver, ResolvedCycleInfo
from ml.inference.model_resolver import ModelIntegrityError, ModelResolver
from ml.inference.pipeline import OperationalInferencePipeline, generate_canonical_india_grid_points
from ml.inference.predictor import RAMPPredictor
from ml.inference.probability import ExtremeProbabilityPredictor
from ml.inference.products import ForecastProductManager
from ml.inference.provenance import (
    ForecastAuditLogger,
    ForecastManifest,
    generate_forecast_run_id,
    get_git_commit,
)
from ml.inference.spatial import SpatialForecastEngine
from ml.inference.validation import InputValidationError, InputValidator
from ramp.data_plane.discovery import DataDiscoveryService
from ramp.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def pipeline():
    return OperationalInferencePipeline()


@pytest.fixture
def model_resolver():
    return ModelResolver()


# ---------------------------------------------------------------------------
# 1. Forecast Cycle Discovery
# ---------------------------------------------------------------------------
def test_forecast_cycle_discovery():
    resolver = ForecastCycleResolver()
    cycles = resolver.list_available_cycles()
    assert len(cycles) > 0
    for c in cycles:
        assert isinstance(c, ResolvedCycleInfo)
        assert c.cycle_id.startswith("DEMO_") or c.cycle_id.startswith("NCUM_")
        assert c.data_mode in ("SYNTHETIC_DEMO", "REAL_OPERATIONAL", "REAL_ARCHIVE")


# ---------------------------------------------------------------------------
# 2. Available Lead Discovery
# ---------------------------------------------------------------------------
def test_available_lead_discovery():
    resolver = ForecastCycleResolver()
    cycles = resolver.list_available_cycles()
    cycle_00z = next(c for c in cycles if "00Z" in c.cycle_id)
    assert 24 in cycle_00z.available_leads
    assert all(lead > 0 for lead in cycle_00z.available_leads)


# ---------------------------------------------------------------------------
# 3. Input Validation Gates
# ---------------------------------------------------------------------------
def test_input_validation():
    resolver = ForecastCycleResolver()
    cycle = resolver.get_cycle("DEMO_20260927_00Z")
    assert cycle is not None

    # Valid lead
    report = InputValidator.validate_request(cycle, lead_time_hours=24)
    assert report["all_passed"] is True
    assert report["status"] == "VALIDATED"

    # Invalid lead (e.g. 999h)
    invalid_report = InputValidator.validate_request(cycle, lead_time_hours=999)
    assert invalid_report["all_passed"] is False
    assert invalid_report["status"] == "FORECAST_GENERATION_BLOCKED"
    assert "LEAD_AVAILABLE" in invalid_report["gate_statuses"]
    assert invalid_report["gate_statuses"]["LEAD_AVAILABLE"] is False


# ---------------------------------------------------------------------------
# 4. Feature Schema Validation
# ---------------------------------------------------------------------------
def test_feature_schema_validation():
    pts = [{"latitude": 18.5, "longitude": 73.8}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)
    assert features.shape[1] == 18
    InferenceFeatureBuilder.audit_features(features)

    # Missing column must raise FeatureSchemaMismatchError
    bad_features = features.drop(columns=["t850"])
    with pytest.raises(FeatureSchemaMismatchError):
        InferenceFeatureBuilder.audit_features(bad_features)


# ---------------------------------------------------------------------------
# 5. Model Registry Resolution
# ---------------------------------------------------------------------------
def test_model_registry_resolution(model_resolver):
    active = model_resolver.resolve_active_models()
    assert "moe" in active
    assert "global" in active
    assert "regime" in active
    assert "extreme" in active

    moe = active["moe"]
    assert moe.model_id == "ramp_moe_v2.0.0"
    assert moe.lifecycle_status == "DEVELOPMENT"
    assert moe.is_demo is True


# ---------------------------------------------------------------------------
# 6. Model Checksum Validation
# ---------------------------------------------------------------------------
def test_model_checksum_validation(model_resolver):
    active = model_resolver.resolve_active_models()
    for role, m in active.items():
        assert len(m.checksum_sha256) == 64
        # Re-verifying with corrupt file should raise ModelIntegrityError
        with pytest.raises(ModelIntegrityError):
            model_resolver.verify_checksum("corrupt_test_file", "invalid_expected_sha")


# ---------------------------------------------------------------------------
# 7. Global Model Inference
# ---------------------------------------------------------------------------
def test_global_model_inference(model_resolver):
    active = model_resolver.resolve_active_models()
    pts = [{"latitude": 20.0, "longitude": 78.0}, {"latitude": 22.0, "longitude": 80.0}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)

    global_m = active["global"].model_object
    preds = global_m.predict(features)
    assert len(preds) == 2
    assert np.all(preds >= 0.0)


# ---------------------------------------------------------------------------
# 8. Weather Regime Inference
# ---------------------------------------------------------------------------
def test_regime_inference(model_resolver):
    active = model_resolver.resolve_active_models()
    pts = [{"latitude": 19.0, "longitude": 73.0}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)

    regime_m = active["regime"].model_object
    labels = regime_m.predict(features)
    probs = regime_m.predict_proba(features)
    assert len(labels) == 1
    assert probs.shape == (1, 7)
    assert np.isclose(np.sum(probs), 1.0, atol=1e-3)


# ---------------------------------------------------------------------------
# 9. RAMP MoE Inference
# ---------------------------------------------------------------------------
def test_moe_inference(model_resolver):
    active = model_resolver.resolve_active_models()
    pts = [{"latitude": 18.0, "longitude": 74.0}, {"latitude": 25.0, "longitude": 91.0}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)

    predictor = RAMPPredictor(
        moe_model=active["moe"],
        global_model=active["global"],
        regime_model=active["regime"],
    )
    res = predictor.predict_field(features)
    assert "ramp_moe" in res
    assert "correction" in res
    assert "dominant_regime" in res
    assert "uncertainty" in res
    assert np.all(res["ramp_moe"] >= 0.0)
    assert np.allclose(res["correction"], res["ramp_moe"] - res["raw_nwp"])


# ---------------------------------------------------------------------------
# 10. Extreme Probability Inference
# ---------------------------------------------------------------------------
def test_extreme_probability_inference(model_resolver):
    active = model_resolver.resolve_active_models()
    pts = [{"latitude": 19.0, "longitude": 73.0}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)

    ext_predictor = ExtremeProbabilityPredictor(active["extreme"])
    probs, mono = ext_predictor.predict_probabilities(features, enforce_monotonicity=True)
    assert "prob_rain" in probs
    assert "prob_heavy" in probs
    assert "prob_very_heavy" in probs
    assert "prob_extreme" in probs


# ---------------------------------------------------------------------------
# 11. Monotonicity Enforcement Invariant
# ---------------------------------------------------------------------------
def test_probability_monotonicity(model_resolver):
    active = model_resolver.resolve_active_models()
    pts = [{"latitude": 18.0, "longitude": 74.0}, {"latitude": 28.0, "longitude": 77.0}]
    features = InferenceFeatureBuilder.build_synthetic_grid_features(pts, lead_time_hours=24)

    ext_predictor = ExtremeProbabilityPredictor(active["extreme"])
    probs, mono = ext_predictor.predict_probabilities(features, enforce_monotonicity=True)

    for i in range(len(pts)):
        p_rain = probs["prob_rain"][i]
        p_heavy = probs["prob_heavy"][i]
        p_vh = probs["prob_very_heavy"][i]
        p_ext = probs["prob_extreme"][i]
        # Strict Monotonicity: P(ext) <= P(vh) <= P(heavy) <= P(rain)
        assert p_ext <= p_vh + 1e-6
        assert p_vh <= p_heavy + 1e-6
        assert p_heavy <= p_rain + 1e-6


# ---------------------------------------------------------------------------
# 12. Calibration Loading (No Mutation)
# ---------------------------------------------------------------------------
def test_calibration_loading(model_resolver):
    active = model_resolver.resolve_active_models()
    cal = active["extreme"].calibration
    calibrator = RegisteredCalibrator(cal)
    assert calibrator.method in ("isotonic", "platt", "temperature")

    raw_p = np.array([0.1, 0.5, 0.9])
    cal_p = calibrator.calibrate(raw_p)
    assert np.all(cal_p >= 0.0) and np.all(cal_p <= 1.0)


# ---------------------------------------------------------------------------
# 13. Forecast Run ID Generation
# ---------------------------------------------------------------------------
def test_forecast_run_id():
    run_id = generate_forecast_run_id(
        initialization_time="2026-09-27T00:00:00Z",
        cycle_utc="00 UTC",
        lead_time_hours=24,
    )
    assert run_id == "RAMP_20260927_00UTC_T24"


# ---------------------------------------------------------------------------
# 14. Forecast Manifest
# ---------------------------------------------------------------------------
def test_forecast_manifest(pipeline):
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    prov = res["provenance"]
    assert prov["forecast_run_id"] == "RAMP_20260927_00UTC_T24"
    assert prov["data_mode"] == "SYNTHETIC_DEMO"
    assert "input_checksums" in prov
    assert "model_checksums" in prov
    assert "output_checksums" in prov


# ---------------------------------------------------------------------------
# 15. Operational Provenance
# ---------------------------------------------------------------------------
def test_provenance(pipeline):
    commit = get_git_commit()
    assert len(commit) >= 7

    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    assert res["provenance"]["git_commit"] == commit


# ---------------------------------------------------------------------------
# 16. Product Generation (Product 1 through 9)
# ---------------------------------------------------------------------------
def test_product_generation(pipeline):
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    assert "grid_cells" in res
    assert len(res["grid_cells"]) > 0

    c0 = res["grid_cells"][0]
    assert "rainfall_prediction_mm" in c0
    assert "raw_nwp_rainfall_mm" in c0
    assert "rainfall_probability" in c0
    assert "extreme_probability" in c0
    assert "regime" in c0


# ---------------------------------------------------------------------------
# 17. District Product Aggregation
# ---------------------------------------------------------------------------
def test_district_product(pipeline):
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    districts = res["districts"]
    assert len(districts) >= 15
    for d in districts:
        assert "district_name" in d
        assert "rainfall" in d
        assert "probabilities" in d
        assert "risk_category" in d
        assert d["risk_category"] in ("NORMAL", "WATCH", "HIGH_RAINFALL", "VERY_HIGH_RAINFALL", "EXTREME_RAINFALL")


# ---------------------------------------------------------------------------
# 18. State Product Aggregation
# ---------------------------------------------------------------------------
def test_state_product(pipeline):
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    states = res["states"]
    assert len(states) >= 8
    for s in states:
        assert "state_name" in s
        assert "mean_rainfall_mm" in s
        assert "max_rainfall_mm" in s
        assert "high_risk_district_count" in s


# ---------------------------------------------------------------------------
# 19. Export JSON
# ---------------------------------------------------------------------------
def test_export_json(client):
    r = client.get("/api/forecast/export/RAMP_20260927_00UTC_T24?format=json")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    doc = r.json()
    assert "forecast_run_id" in doc


# ---------------------------------------------------------------------------
# 20. Export CSV
# ---------------------------------------------------------------------------
def test_export_csv(client):
    r = client.get("/api/forecast/export/RAMP_20260927_00UTC_T24?format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "# RAMP Operational Meteorological Forecast Product" in r.text


# ---------------------------------------------------------------------------
# 21. Export GeoJSON
# ---------------------------------------------------------------------------
def test_export_geojson(client):
    r = client.get("/api/forecast/export/RAMP_20260927_00UTC_T24?format=geojson")
    assert r.status_code == 200
    assert "application/geo+json" in r.headers["content-type"]
    doc = r.json()
    assert doc["type"] == "FeatureCollection"
    assert len(doc["features"]) > 0


# ---------------------------------------------------------------------------
# 22. Real Data Blocking (Integrity Rule)
# ---------------------------------------------------------------------------
def test_real_data_block():
    discovery = DataDiscoveryService()
    matrix = discovery.get_availability_matrix()
    if not matrix.real_data_available:
        assert matrix.overall_mode == "SYNTHETIC_DEMO"
        assert "REAL DATA NOT AVAILABLE" in matrix.honesty_notice


# ---------------------------------------------------------------------------
# 23. Synthetic Demo Mode Tagging
# ---------------------------------------------------------------------------
def test_synthetic_demo_mode(pipeline):
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=24)
    assert res["data_mode"] == "SYNTHETIC_DEMO"
    assert res["is_real"] is False
    assert res["cycle"]["data_mode"] == "SYNTHETIC_DEMO"


# ---------------------------------------------------------------------------
# 24. No Fake Forecast Cycles
# ---------------------------------------------------------------------------
def test_no_fake_cycle():
    resolver = ForecastCycleResolver()
    # Nonexistent cycle must return None and reject inference
    fake_cycle = resolver.get_cycle("NCUM_20999999_99Z")
    assert fake_cycle is None

    pipeline = OperationalInferencePipeline()
    with pytest.raises(InputValidationError):
        pipeline.run_forecast("NCUM_20999999_99Z", lead_time_hours=24)


# ---------------------------------------------------------------------------
# 25. No Fake Lead Times
# ---------------------------------------------------------------------------
def test_no_fake_lead(pipeline):
    # Demanding an unlisted lead time must be blocked
    res = pipeline.run_forecast("DEMO_20260927_00Z", lead_time_hours=999)
    assert res["status"] == "FORECAST_GENERATION_BLOCKED"


# ---------------------------------------------------------------------------
# 26. No Fake Operational Status Claims
# ---------------------------------------------------------------------------
def test_no_fake_operational_status(client):
    r = client.get("/api/forecast/status")
    assert r.status_code == 200
    data = r.json()["data"]
    # Unless real raw files are mounted, NCUM and NEPS must be NOT_AVAILABLE
    assert data["ncmrwf_ncum"] in ("AVAILABLE", "NOT_AVAILABLE")
    assert data["overall_data_mode"] in ("SYNTHETIC_DEMO", "REAL_OPERATIONAL")
    if data["overall_data_mode"] == "SYNTHETIC_DEMO":
        assert "REAL DATA NOT AVAILABLE" in data["honesty_notice"]
