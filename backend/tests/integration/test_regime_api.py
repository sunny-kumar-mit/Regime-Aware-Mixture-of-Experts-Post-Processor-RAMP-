"""
Integration Tests for RAMP Weather Regime API Router
SIH26080 | /api/regime/* endpoints
MoES / NCMRWF
"""

from fastapi.testclient import TestClient
import numpy as np
import pytest

from ml.regimes.definitions import REGIME_ORDER
from ramp.main import app

client = TestClient(app)


def test_api_regime_status():
    """GET /api/regime/status returns operational status, 7 regimes, and honest synthetic data mode."""
    resp = client.get("/api/regime/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "OPERATIONAL"
    assert data["real_data_available"] is False
    assert data["data_mode"] == "SYNTHETIC_DEMO"
    assert data["num_regimes"] == 7
    assert len(data["regimes"]) == 7
    for reg in REGIME_ORDER:
        assert reg.value in data["regimes"]


def test_api_regime_models():
    """GET /api/regime/models lists registered models with metadata and hyperparameters."""
    resp = client.get("/api/regime/models")
    assert resp.status_code == 200
    data = resp.json()

    assert "total" in data
    assert data["total"] >= 1
    assert "models" in data
    first_model = data["models"][0]
    assert "model_id" in first_model
    assert "model_type" in first_model
    assert "features" in first_model


def test_api_regime_current():
    """GET /api/regime/current returns probability vector, entropy, and uncertainty."""
    resp = client.get("/api/regime/current")
    assert resp.status_code == 200
    data = resp.json()

    assert "top_regime" in data
    assert data["top_regime"] in [r.value for r in REGIME_ORDER]
    assert "probabilities" in data
    assert len(data["probabilities"]) == 7

    prob_sum = sum(data["probabilities"].values())
    assert np.isclose(prob_sum, 1.0, atol=1e-3)

    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0
    assert "entropy" in data
    assert "normalized_entropy" in data
    assert "uncertainty_level" in data
    assert data["uncertainty_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "feature_availability" in data


def test_api_regime_grid():
    """GET /api/regime/grid returns spatial probability layers."""
    resp = client.get("/api/regime/grid")
    assert resp.status_code == 200
    data = resp.json()

    assert "total_points" in data
    assert "layers" in data
    assert "top_regimes" in data


def test_api_regime_metrics():
    """GET /api/regime/metrics returns performance with explicit synthetic demonstration notice."""
    resp = client.get("/api/regime/metrics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["data_mode"] == "SYNTHETIC_DEMO"
    assert "SYNTHETIC DEMONSTRATION ONLY" in data["performance_notice"]
    assert "metrics" in data
    assert "confusion_matrix" in data
    assert "class_distribution" in data


def test_api_regime_calibration():
    """GET /api/regime/calibration returns validation calibration diagnostics."""
    resp = client.get("/api/regime/calibration")
    assert resp.status_code == 200
    data = resp.json()

    assert "calibration_method" in data
    assert "uncalibrated" in data
    assert "calibrated" in data
    assert "brier_score" in data["uncalibrated"]
    assert "brier_score" in data["calibrated"]


def test_api_regime_transitions():
    """GET /api/regime/transitions returns sequential trajectory and transition state."""
    resp = client.get("/api/regime/transitions")
    assert resp.status_code == 200
    data = resp.json()

    assert "transition_state" in data
    assert "transitions_detected" in data
    assert "history" in data
    assert "max_tvd" in data


def test_api_regime_sample_not_found():
    """GET /api/regime/{sample_id} returns 404 for invalid/missing sample ID."""
    resp = client.get("/api/regime/NONEXISTENT_SAMPLE_XYZ_999")
    assert resp.status_code == 404
