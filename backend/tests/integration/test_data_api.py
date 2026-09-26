"""
API Integration Tests — Data Layer Endpoints
SIH26080 | /api/data/* endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
from ramp.main import app

client = TestClient(app)


class TestDataProvidersEndpoint:
    def test_list_providers_returns_200(self):
        resp = client.get("/api/data/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "total" in data
        assert isinstance(data["providers"], list)
        assert data["total"] >= 1

    def test_providers_have_required_fields(self):
        resp = client.get("/api/data/providers")
        for p in resp.json()["providers"]:
            assert "provider_id" in p
            assert "name" in p
            assert "provider_type" in p
            assert "status" in p

    def test_get_existing_provider(self):
        resp = client.get("/api/data/providers/gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_id"] == "gfs"

    def test_get_nonexistent_provider_404(self):
        resp = client.get("/api/data/providers/nonexistent_provider_xyz")
        assert resp.status_code == 404

    def test_synthetic_provider_present(self):
        """Synthetic provider must be in registry for demo/testing."""
        resp = client.get("/api/data/providers")
        ids = [p["provider_id"] for p in resp.json()["providers"]]
        assert "synthetic_nwp" in ids

    def test_ncmrwf_provider_not_available(self):
        """NCMRWF must not be listed as AVAILABLE in this environment."""
        resp = client.get("/api/data/providers/ncmrwf_ncum")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] != "AVAILABLE", (
            "NCMRWF should NOT be AVAILABLE in this environment. "
            "Institutional data access is required."
        )


class TestDataDatasetsEndpoint:
    def test_list_datasets_returns_200(self):
        resp = client.get("/api/data/datasets")
        assert resp.status_code == 200
        data = resp.json()
        assert "datasets" in data
        assert "total" in data

    def test_imd_dataset_in_manifest(self):
        resp = client.get("/api/data/datasets/imd_rainfall_025")
        assert resp.status_code == 200
        ds = resp.json()
        assert ds["id"] == "imd_rainfall_025"
        assert ds["provider"] == "IMD"

    def test_gfs_dataset_in_manifest(self):
        resp = client.get("/api/data/datasets/gfs_025")
        assert resp.status_code == 200

    def test_ncmrwf_dataset_marked_unavailable(self):
        resp = client.get("/api/data/datasets/ncmrwf_ncum")
        assert resp.status_code == 200
        ds = resp.json()
        assert ds["status"] == "UNAVAILABLE", (
            "NCMRWF dataset must be marked UNAVAILABLE in manifest."
        )

    def test_dataset_not_found_404(self):
        resp = client.get("/api/data/datasets/nonexistent_xyz")
        assert resp.status_code == 404


class TestDataStatusEndpoint:
    def test_status_returns_200(self):
        resp = client.get("/api/data/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "ready_for_ml" in data
        assert "readiness_message" in data
        assert "timestamp" in data
        assert "providers" in data

    def test_status_has_correct_types(self):
        resp = client.get("/api/data/status")
        data = resp.json()
        assert isinstance(data["ready_for_ml"], bool)
        assert isinstance(data["providers_available"], int)
        assert isinstance(data["providers_not_configured"], int)


class TestValidateProviderEndpoint:
    def test_validate_gfs(self):
        resp = client.post("/api/data/validate/gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert "passed" in data
        assert "errors" in data
        assert "data_mode" in data

    def test_validate_synthetic_passes(self):
        resp = client.post("/api/data/validate/synthetic_nwp")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_mode"] == "SYNTHETIC_DEMO"

    def test_validate_nonexistent_404(self):
        resp = client.post("/api/data/validate/nonexistent_xyz")
        assert resp.status_code == 404


class TestVariableSchemaEndpoint:
    def test_known_variable(self):
        resp = client.get("/api/data/schema/precip_nwp_raw")
        assert resp.status_code == 200
        data = resp.json()
        assert data["standard_units"] == "mm"
        assert data["physical_min"] == 0.0
        assert data["extreme_threshold"] == 300.0

    def test_observed_rainfall_schema(self):
        resp = client.get("/api/data/schema/observed_rainfall_mm")
        assert resp.status_code == 200
        data = resp.json()
        assert data["physical_min"] == 0.0
        assert data["extreme_threshold"] == 300.0

    def test_unknown_variable_404(self):
        resp = client.get("/api/data/schema/unknown_var_xyz")
        assert resp.status_code == 404
