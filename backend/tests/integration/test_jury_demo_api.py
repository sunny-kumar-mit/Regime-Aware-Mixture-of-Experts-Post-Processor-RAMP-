"""
Integration Tests: Phase 22 — Jury Demo REST API
SIH26080 | /api/jury/* and /api/scientific/jury-demo Endpoints
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

# Ensure root workspace is on path
WORKSPACE = Path(__file__).resolve().parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from ramp.main import app

client = TestClient(app)


def test_get_jury_cases():
    res = client.get("/api/jury/cases")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert len(data["data"]) >= 5
    case_ids = [c["case_id"] for c in data["data"]]
    assert "CASE_001" in case_ids
    assert "CASE_002" in case_ids
    assert "CASE_003" in case_ids
    assert "CASE_004" in case_ids
    assert "CASE_005" in case_ids


def test_get_jury_case_detail():
    res = client.get("/api/jury/cases/CASE_001")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    c = data["data"]
    assert c["case_id"] == "CASE_001"
    assert c["district"] == "Nagpur"
    assert c["state"] == "Maharashtra"
    assert c["regime"] == "LOW_DEPRESSION"
    assert c["nwp_rainfall_mm"] == 42.5
    assert c["ramp_prediction_mm"] == 38.2
    assert "pipeline_stages" in c
    assert len(c["pipeline_stages"]) >= 8


def test_get_jury_case_pipeline():
    res = client.get("/api/jury/cases/CASE_001/pipeline")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    stages = data["data"]
    stage_names = [s["stage"] for s in stages]
    assert "NWP_INPUT" in stage_names
    assert "REGIME_DETECTION" in stage_names
    assert "BASELINE_CORRECTION" in stage_names
    assert "RAMP_MOE" in stage_names
    assert "EXTREME_PROBABILITY" in stage_names
    assert "SPATIAL_DISTRICT_PRODUCT" in stage_names
    assert "EXPLAINABILITY" in stage_names
    assert "VERIFICATION" in stage_names


def test_get_jury_case_regime():
    res = client.get("/api/jury/cases/CASE_001/regime")
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["dominant_regime"] == "LOW_DEPRESSION"
    assert "regime_probabilities" in data["data"]
    assert data["data"]["regime_probabilities"]["LOW_DEPRESSION"] == 0.62


def test_get_jury_case_experts():
    res = client.get("/api/jury/cases/CASE_001/experts")
    assert res.status_code == 200
    data = res.json()
    assert "expert_weights" in data["data"]
    assert data["data"]["top_expert"] == "LOW_DEPRESSION_EXPERT"
    assert data["data"]["top_expert_weight"] == 0.62
    assert "why_expert" in data["data"]


def test_get_jury_case_extreme_risk():
    res = client.get("/api/jury/cases/CASE_001/extreme-risk")
    assert res.status_code == 200
    data = res.json()
    assert "rain" in data["data"]
    assert "heavy" in data["data"]
    assert "very_heavy" in data["data"]
    assert "extreme" in data["data"]


def test_get_jury_case_spatial():
    res = client.get("/api/jury/cases/CASE_001/spatial")
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["district"] == "Nagpur"
    assert data["data"]["state"] == "Maharashtra"
    assert data["data"]["ramp_rainfall_mm"] == 38.2
    assert data["data"]["raw_nwp_rainfall_mm"] == 42.5
    assert len(data["data"]["affected_districts"]) >= 1


def test_get_jury_case_explainability():
    res = client.get("/api/jury/cases/CASE_001/explainability")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]["top_features"]) >= 1
    assert "why_expert" in data["data"]


def test_get_jury_case_verification():
    res = client.get("/api/jury/cases/CASE_001/verification")
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["status"] == "VERIFICATION_NOT_AVAILABLE"
    assert "not currently mounted" in data["data"]["reason"]


def test_post_jury_run_case():
    res = client.post("/api/jury/cases/CASE_001/run")
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["case_id"] == "CASE_001"
    assert data["data"]["status"] == "COMPLETED"
    run_id = data["data"]["run_id"]
    assert run_id.startswith("RUN_CASE_001_")

    # Check status of this run
    status_res = client.get(f"/api/jury/runs/{run_id}")
    assert status_res.status_code == 200
    assert status_res.json()["data"]["status"] == "COMPLETED"


def test_get_scientific_jury_demo():
    res = client.get("/api/scientific/jury-demo")
    assert res.status_code == 200
    data = res.json()
    assert "stages" in data["data"]
    assert "benchmark_summary" in data["data"]
    assert "case_studies" in data["data"]
