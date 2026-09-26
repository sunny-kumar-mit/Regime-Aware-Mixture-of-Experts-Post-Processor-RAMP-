"""
Root Integration Health Check
SIH26080 | System-level integration test
"""

from fastapi.testclient import TestClient
from ramp.main import app
from ramp.config import settings

client = TestClient(app)


def test_system_overall_health():
    """Verify that root probes and API contracts are accessible."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    api_resp = client.get(f"{settings.API_PREFIX}/health")
    assert api_resp.status_code == 200
    assert api_resp.json()["data_mode"] == settings.RAMP_DATA_MODE
