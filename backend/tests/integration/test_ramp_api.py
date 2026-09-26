"""
Integration Tests: RAMP Mixture-of-Experts REST API
SIH26080 | /api/ramp/* Endpoints
"""

from fastapi.testclient import TestClient
import pytest

from ramp.main import app

client = TestClient(app)


def test_get_ramp_status():
    res = client.get("/api/ramp/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert "data_mode" in data
    assert "SYNTHETIC DEMONSTRATION ONLY" in data["performance_notice"]
    assert data["expert_count"] == 7
    assert data["active_model_id"] == "ramp_v1.0.0"


def test_list_ramp_models():
    res = client.get("/api/ramp/models")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "models" in data
    assert data["total"] >= 1


def test_get_current_model():
    res = client.get("/api/ramp/current")
    assert res.status_code == 200
    data = res.json()
    assert "metadata" in data
    assert "model_card" in data
    assert data["metadata"]["ramp_model_id"] == "ramp_v1.0.0"


def test_get_expert_details():
    res = client.get("/api/ramp/experts")
    assert res.status_code == 200
    data = res.json()
    assert "experts" in data
    assert "ACTIVE_MONSOON" in data["experts"]
    assert "BREAK_MONSOON" in data["experts"]


def test_get_gating_diagnostics():
    res = client.get("/api/ramp/gating")
    assert res.status_code == 200
    data = res.json()
    assert "diagnostics" in data
    assert "sample_count" in data["diagnostics"]
    assert "mean_entropy" in data["diagnostics"]


def test_get_ramp_metrics():
    res = client.get("/api/ramp/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "ramp" in data["metrics"]
    assert "rmse" in data["metrics"]["ramp"]


def test_get_ramp_lead_time_metrics():
    res = client.get("/api/ramp/metrics/lead-time")
    assert res.status_code == 200
    data = res.json()
    assert "lead_time_metrics" in data


def test_get_ramp_threshold_metrics():
    res = client.get("/api/ramp/metrics/threshold")
    assert res.status_code == 200
    data = res.json()
    assert "threshold_metrics" in data
    assert "ramp" in data["threshold_metrics"]


def test_get_ramp_regime_metrics():
    res = client.get("/api/ramp/metrics/regime")
    assert res.status_code == 200
    data = res.json()
    assert "regime_metrics" in data


def test_get_ramp_spatial_metrics():
    res = client.get("/api/ramp/metrics/spatial")
    assert res.status_code == 200
    data = res.json()
    assert "spatial_metrics" in data


def test_get_ramp_benchmark():
    res = client.get("/api/ramp/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert "benchmark_matrix" in data
    assert "bootstrap_significance" in data
    models = [r["model"] for r in data["benchmark_matrix"]]
    assert "raw_nwp" in models
    assert "global_ml" in models
    assert "ramp" in models


def test_get_ramp_diagnostics():
    res = client.get("/api/ramp/diagnostics")
    assert res.status_code == 200
    data = res.json()
    assert "expert_diversity" in data
    assert "ablation_comparison" in data


def test_get_ramp_prediction_sample():
    # beb63898945bcbe3 exists in test dataset
    res = client.get("/api/ramp/prediction/beb63898945bcbe3")
    assert res.status_code == 200
    data = res.json()
    assert data["sample_id"] == "beb63898945bcbe3"
    assert "ramp_prediction" in data
    assert "gate_probabilities" in data
    assert "expert_predictions" in data
    assert "weighted_contributions" in data
    assert len(data["gate_probabilities"]) == 7
    assert len(data["expert_predictions"]) == 7
    # Non-negativity
    assert data["ramp_prediction"] >= 0.0


def test_get_ramp_prediction_nonexistent():
    res = client.get("/api/ramp/prediction/nonexistent_sample_xyz")
    assert res.status_code == 404
