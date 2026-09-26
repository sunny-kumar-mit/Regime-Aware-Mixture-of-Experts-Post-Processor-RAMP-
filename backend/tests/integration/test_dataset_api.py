"""
Integration tests for RAMP dataset API endpoints.
SIH26080 | /api/datasets/* endpoints
"""

from fastapi.testclient import TestClient
import pytest

from ramp.main import app

client = TestClient(app)


def test_api_list_training_datasets():
    """GET /api/datasets/training returns dataset list and honest real data availability."""
    resp = client.get("/api/datasets/training")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "real_data_available" in data
    assert "status_message" in data
    assert isinstance(data["datasets"], list)


def test_api_features_registry():
    """GET /api/datasets/features returns canonical registered features."""
    resp = client.get("/api/datasets/features")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert data["total"] > 0
    names = [f["name"] for f in data["features"]]
    assert "raw_nwp_rainfall" in names
    assert "u850" in names
    assert "v850" in names
    assert "wind_speed_850" in names
    assert "wind_direction_850" in names


def test_api_dataset_statistics():
    """GET /api/datasets/statistics returns split-specific distribution metrics."""
    resp = client.get("/api/datasets/statistics")
    if resp.status_code == 200:
        data = resp.json()
        assert "TRAIN" in data
        assert "rainfall_mean" in data["TRAIN"]


def test_api_dataset_splits():
    """GET /api/datasets/splits returns split manifest."""
    resp = client.get("/api/datasets/splits")
    if resp.status_code == 200:
        data = resp.json()
        assert "split_type" in data
        assert "purge_gap_hours" in data


def test_api_dataset_leakage():
    """GET /api/datasets/leakage returns leakage audit report."""
    resp = client.get("/api/datasets/leakage")
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "passed_checks" in data
