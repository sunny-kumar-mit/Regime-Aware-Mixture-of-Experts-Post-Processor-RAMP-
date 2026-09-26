"""
Unit Tests for RAMP API Endpoints
SIH26080 | Health, Version, and System Info Contracts
"""

from fastapi.testclient import TestClient
from ramp.main import app
from ramp.config import settings

client = TestClient(app)


def test_api_health():
    """Test /api/health returns 200 and conforms to HealthResponse schema."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.APP_ENV
    assert data["data_mode"] == settings.RAMP_DATA_MODE


def test_api_version():
    """Test /api/version returns version information."""
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == settings.VERSION
    assert data["app_name"] == settings.APP_NAME


def test_api_system_info():
    """Test /api/system/info returns valid metadata and 7 regime types."""
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == settings.APP_NAME
    assert data["data_mode"] == settings.RAMP_DATA_MODE
    assert len(data["active_regimes"]) == 7
    assert "ACTIVE_MONSOON" in data["active_regimes"]
    assert "BREAK_MONSOON" in data["active_regimes"]
    assert "MONSOON_LOW_DEPRESSION" in data["active_regimes"]
    assert "COASTAL_RAINFALL" in data["active_regimes"]
    assert "OROGRAPHIC_RAINFALL" in data["active_regimes"]
    assert "WESTERN_DISTURBANCE" in data["active_regimes"]
    assert "TRANSITION_OTHER" in data["active_regimes"]
    # Check IMD thresholds
    thresholds = data["imd_thresholds_mm_per_24h"]
    assert thresholds["heavy"] == 64.5
    assert thresholds["very_heavy"] == 115.6
    assert thresholds["extremely_heavy"] == 204.5


def test_cors_headers():
    """Test that CORS headers are appropriately configured."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Status code 200 for allowed origin
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
