"""
RAMP Phase 12 Test Suite: Real Paired Dataset & Operational Data Plane
SIH26080 | Regime-Aware Mixture-of-Experts Post-Processor (RAMP)
MoES / NCMRWF

Validates:
  - test_real_dataset_discovery
  - test_real_pairing
  - test_timestamp_alignment
  - test_future_observation_rejection
  - test_missing_observation
  - test_missing_forecast
  - test_coordinate_alignment
  - test_unit_consistency
  - test_duplicate_records
  - test_extreme_event_preservation
  - test_chronological_split
  - test_no_random_temporal_split
  - test_leakage_report
  - test_dataset_manifest
  - test_checksum_manifest
  - test_data_mode_integrity
  - test_dataset_real_api_endpoints
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml.datasets.real.pipeline import (
    RealDatasetPipeline,
    RAIN_THRESHOLD_MM,
    HEAVY_THRESHOLD_MM,
    VERY_HEAVY_THRESHOLD_MM,
    EXTREME_THRESHOLD_MM,
    ALLOWED_FEATURE_NAMES,
    FORBIDDEN_FEATURE_NAMES,
)
from ramp.data_plane.matcher import DataMatchingEngine, MatchStatus
from ramp.data_plane.sources import DataMode
from ramp.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_dataset_dir(tmp_path):
    d = tmp_path / "test_ramp_real_v1"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# 1. Discovery & Data Mode Integrity
# ---------------------------------------------------------------------------

def test_real_dataset_discovery():
    """Verify discovery service correctly reports unmounted real archives without fabrication."""
    pipeline = RealDatasetPipeline()
    disc = pipeline.discover_operational_sources()
    assert "matrix" in disc
    assert "scans" in disc
    assert disc["overall_mode"] in [DataMode.SYNTHETIC_DEMO.value, DataMode.REAL_OPERATIONAL.value]
    assert disc["real_data_available"] is False  # In this environment raw archives are unmounted


def test_data_mode_integrity():
    """Verify strict prohibition of fake real labels when running unmounted."""
    pipeline = RealDatasetPipeline()
    readiness = pipeline.inspect_pipeline_readiness()
    assert readiness["status"] == "NOT_AVAILABLE"
    assert "real NCMRWF/IMD archive not mounted" in readiness["message"]


# ---------------------------------------------------------------------------
# 2. Pairing & Temporal Alignment Engine
# ---------------------------------------------------------------------------

def test_real_pairing():
    """Verify pairing between NWP valid time and IMD observation time."""
    init_dt = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    lead_hours = 24
    valid_dt = init_dt + timedelta(hours=lead_hours)

    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_dt,
        lead_time_hours=lead_hours,
        observation_time=valid_dt,
        model_name="NCUM",
        provider_id="ncmrwf_ncum",
        obs_provider_id="imd_obs",
        forecast_grid_present=True,
        obs_grid_present=True,
        obs_missing_fraction=0.03,
        extreme_obs_count=5,
    )
    assert res.status == MatchStatus.MATCHED
    assert res.time_offset_seconds == 0.0
    assert res.is_temporally_valid is True
    assert res.leakage_violation is False


def test_timestamp_alignment():
    """Verify misalignment is caught when forecast valid time != observation time."""
    init_dt = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    lead_hours = 24
    wrong_obs_dt = init_dt + timedelta(hours=36)  # 12h offset

    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_dt,
        lead_time_hours=lead_hours,
        observation_time=wrong_obs_dt,
        model_name="NCUM",
        provider_id="ncmrwf_ncum",
        obs_provider_id="imd_obs",
        forecast_grid_present=True,
        obs_grid_present=True,
    )
    assert res.status == MatchStatus.MISALIGNED
    assert res.time_offset_seconds == 12 * 3600


def test_future_observation_rejection():
    """Anti-leakage: observation time cannot precede initialization time or violate causality."""
    init_dt = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    # Observation timestamp occurs in the past/future relative to valid time
    past_obs_dt = init_dt - timedelta(hours=6)

    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_dt,
        lead_time_hours=24,
        observation_time=past_obs_dt,
        model_name="NCUM",
        provider_id="ncmrwf_ncum",
        obs_provider_id="imd_obs",
    )
    assert res.is_temporally_valid is False or res.leakage_violation is True


def test_missing_observation():
    """Verify handling when forecast grid is present but observation grid is missing."""
    init_dt = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_dt,
        lead_time_hours=24,
        observation_time=init_dt + timedelta(hours=24),
        model_name="NCUM",
        provider_id="ncmrwf_ncum",
        obs_provider_id="imd_obs",
        forecast_grid_present=True,
        obs_grid_present=False,
    )
    assert res.status == MatchStatus.MISSING_OBSERVATION


def test_missing_forecast():
    """Verify handling when observation is present but NWP forecast is missing."""
    init_dt = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_dt,
        lead_time_hours=24,
        observation_time=init_dt + timedelta(hours=24),
        model_name="NCUM",
        provider_id="ncmrwf_ncum",
        obs_provider_id="imd_obs",
        forecast_grid_present=False,
        obs_grid_present=True,
    )
    assert res.status == MatchStatus.MISSING_FORECAST


# ---------------------------------------------------------------------------
# 3. Quality Control, Units, Coordinates, Extremes
# ---------------------------------------------------------------------------

def test_coordinate_alignment(temp_dataset_dir):
    """Verify India domain bounding box enforcement (6.5–38.5°N, 66.5–100.5°E)."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    res = pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)
    assert res["status"] == "AVAILABLE"

    df = pd.read_parquet(temp_dataset_dir / "ramp_dataset_real.parquet")
    assert (df["latitude"] >= 6.5).all()
    assert (df["latitude"] <= 38.5).all()
    assert (df["longitude"] >= 66.5).all()
    assert (df["longitude"] <= 100.5).all()


def test_unit_consistency(temp_dataset_dir):
    """Verify standard units across rainfall (mm), wind (m/s), mslp (hPa)."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)

    df = pd.read_parquet(temp_dataset_dir / "ramp_dataset_real.parquet")
    assert (df["observed_rainfall_mm"] >= 0.0).all()
    assert (df["precip_nwp_raw"] >= 0.0).all()
    assert (df["mslp"] > 900.0).all()
    assert (df["mslp"] < 1050.0).all()


def test_duplicate_records(temp_dataset_dir):
    """Verify no duplicate (timestamp, lat, lon) records exist in the paired dataset."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)

    df = pd.read_parquet(temp_dataset_dir / "ramp_dataset_real.parquet")
    dups = df.duplicated(subset=["forecast_valid_time", "latitude", "longitude"]).sum()
    assert dups == 0


def test_extreme_event_preservation(temp_dataset_dir):
    """Verify extreme rainfall values (>204.5mm) are never clipped or zeroed."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=150)

    df = pd.read_parquet(temp_dataset_dir / "ramp_dataset_real.parquet")
    extreme_records = df[df["observed_rainfall_mm"] >= EXTREME_THRESHOLD_MM]
    assert len(extreme_records) > 0
    # Ensure they have extreme flag
    for _, row in extreme_records.iterrows():
        assert row["extreme_label"] == 1
        assert "VALID_EXTREME" in row["quality_flags"]


# ---------------------------------------------------------------------------
# 4. Chronological Splitting & Anti-Leakage
# ---------------------------------------------------------------------------

def test_chronological_split(temp_dataset_dir):
    """Verify chronological split guarantees TRAIN end <= VAL start <= TEST start."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=100)

    train_df = pd.read_parquet(temp_dataset_dir / "train.parquet")
    val_df = pd.read_parquet(temp_dataset_dir / "val.parquet")
    test_df = pd.read_parquet(temp_dataset_dir / "test.parquet")

    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0

    assert train_df["forecast_valid_time"].max() <= val_df["forecast_valid_time"].min()
    assert val_df["forecast_valid_time"].max() <= test_df["forecast_valid_time"].min()


def test_no_random_temporal_split(temp_dataset_dir):
    """Verify partitions are strictly sequential, not shuffled."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=100)

    with open(temp_dataset_dir / "split_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "Chronological" in manifest["splitting_strategy"]
    assert manifest["train_samples"] > manifest["validation_samples"]


def test_leakage_report(temp_dataset_dir):
    """Verify zero forbidden observation columns enter the predictor set X."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)

    with open(temp_dataset_dir / "leakage_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["leakage_detected"] is False
    assert rep["status"] == "PASSED"
    assert len(rep["forbidden_columns_in_x"]) == 0


# ---------------------------------------------------------------------------
# 5. Manifests, Checksums, and Card Validation
# ---------------------------------------------------------------------------

def test_dataset_manifest(temp_dataset_dir):
    """Verify all 10 required dataset metadata artifacts are written."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)

    required_artifacts = [
        "dataset_manifest.json",
        "dataset_card.md",
        "dataset_statistics.json",
        "source_manifest.json",
        "leakage_report.json",
        "qc_report.json",
        "split_manifest.json",
        "event_distribution.json",
        "spatial_coverage.json",
        "checksum_manifest.json",
    ]
    for art in required_artifacts:
        assert (temp_dataset_dir / art).exists(), f"Missing artifact: {art}"


def test_checksum_manifest(temp_dataset_dir):
    """Verify SHA-256 cryptographic hashes are computed for all exported Parquet files."""
    pipeline = RealDatasetPipeline(output_dir=temp_dataset_dir)
    pipeline.build_dataset(force_synthetic_fixture=True, sample_count=50)

    with open(temp_dataset_dir / "checksum_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "sha256" in manifest
    assert "train.parquet" in manifest["sha256"]
    assert len(manifest["sha256"]["train.parquet"]) == 64  # Valid SHA-256 length


# ---------------------------------------------------------------------------
# 6. Real Dataset API Endpoints
# ---------------------------------------------------------------------------

def test_dataset_real_api_endpoints(client):
    """Verify all 8 Phase 12 API endpoints return 200 with standard envelope."""
    endpoints = [
        "/api/datasets/real/status",
        "/api/datasets/real/sources",
        "/api/datasets/real/coverage",
        "/api/datasets/real/statistics",
        "/api/datasets/real/events",
        "/api/datasets/real/splits",
        "/api/datasets/real/quality",
        "/api/datasets/real/provenance",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Failed on endpoint {ep}"
        body = res.json()
        assert "dataset_version" in body
        assert "data_mode" in body
        assert "source" in body
        assert "timestamp" in body
        assert "provenance" in body
        assert "availability_status" in body
        assert "data" in body
