"""
Integration Tests for Phase 5 Baseline APIs
SIH26080 | MoES / NCMRWF
"""

import pytest
from fastapi.testclient import TestClient
from ramp.main import app

client = TestClient(app)


def test_baseline_status_endpoint():
    response = client.get("/api/baselines/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "data_mode" in data
    assert data["data_mode"] == "SYNTHETIC_DEMO"
    assert data["real_data_available"] is False
    assert "models_available" in data
    assert len(data["models_available"]) >= 4


def test_baseline_models_catalog():
    response = client.get("/api/baselines/models")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "models" in data
    assert data["total"] >= 4
    model_ids = [m["model_id"] for m in data["models"]]
    assert "raw_nwp_v1" in model_ids
    assert "mean_bias_v1" in model_ids
    assert "quantile_mapping_v1" in model_ids
    assert "global_lgbm_v1" in model_ids


def test_baseline_overall_metrics():
    response = client.get("/api/baselines/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["data_mode"] == "SYNTHETIC_DEMO"
    assert "SYNTHETIC DEMONSTRATION ONLY" in data["performance_notice"]
    assert "metrics" in data
    metrics = data["metrics"]
    for m in ["raw_nwp", "mean_bias", "quantile_mapping", "global_ml"]:
        assert m in metrics
        assert "rmse" in metrics[m]
        assert "mae" in metrics[m]
        assert "mean_bias" in metrics[m]


def test_baseline_lead_time_metrics():
    response = client.get("/api/baselines/metrics/lead-time")
    assert response.status_code == 200
    data = response.json()
    assert "Day_1_24h" in data
    assert "models" in data["Day_1_24h"]
    assert "raw_nwp" in data["Day_1_24h"]["models"]


def test_baseline_threshold_metrics():
    response = client.get("/api/baselines/metrics/threshold")
    assert response.status_code == 200
    data = response.json()
    for m in ["raw_nwp", "mean_bias", "quantile_mapping", "global_ml"]:
        assert m in data
        assert "heavy_rainfall" in data[m]
        assert "csi" in data[m]["heavy_rainfall"]


def test_baseline_regime_diagnostics():
    response = client.get("/api/baselines/metrics/regime")
    assert response.status_code == 200
    data = response.json()
    assert "ACTIVE_MONSOON" in data
    assert "BREAK_MONSOON" in data
    assert "models" in data["ACTIVE_MONSOON"]
    assert "raw_nwp" in data["ACTIVE_MONSOON"]["models"]
    assert "global_ml" in data["ACTIVE_MONSOON"]["models"]


def test_baseline_benchmark_master():
    response = client.get("/api/baselines/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "benchmark_matrix" in data
    assert "bootstrap_significance" in data
    assert "data_mode" in data
    assert data["data_mode"] == "SYNTHETIC_DEMO"


def test_baseline_spatial_metrics():
    response = client.get("/api/baselines/spatial")
    assert response.status_code == 200
    data = response.json()
    assert "spatial_points" in data
    assert len(data["spatial_points"]) > 0
    pt = data["spatial_points"][0]
    assert "latitude" in pt
    assert "longitude" in pt
    assert "models" in pt


def test_baseline_sample_prediction_not_found():
    response = client.get("/api/baselines/prediction/non_existent_sample_xyz")
    assert response.status_code == 404
