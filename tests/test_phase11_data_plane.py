"""
Phase 11 Unit and Integration Test Suite — Operational Data Plane
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Covers all 12 test requirements specified in Section 14:
1. Source discovery & provider hierarchy
2. Real vs synthetic classification & anti-mislabeling guard
3. Forecast cycle discovery (00, 06, 12, 18 UTC) — no fabrication
4. Dynamic lead time discovery & normalization
5. Coordinate detection (lat, lon, time, ordering normalization)
6. Unit detection & metadata verification
7. Timestamp matching & anti-leakage guard
8. Missing observation handling (NaN preservation, zero-fill prohibition)
9. Duplicate files & timestamp detection
10. Corrupted file quarantine & graceful degradation
11. Checksum (SHA-256) computation
12. Native NCMRWF (0.12°) to RAMP canonical (0.25°) regridding
"""

import hashlib
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from fastapi.testclient import TestClient

from ramp.data_plane.cf_reader import CFMetadataInspector
from ramp.data_plane.cycle import CycleManager, ForecastCycle, LeadTimeNormalizer
from ramp.data_plane.discovery import DataDiscoveryService
from ramp.data_plane.matcher import DataMatchingEngine, MatchStatus
from ramp.data_plane.regridding import NCMRWFGridHarmoniser
from ramp.data_plane.sources import (
    DataMode,
    ProviderHierarchy,
    ProviderTier,
    SOURCE_PROVIDER_SPECS,
    OperationalDatasetMetadata,
)
from ramp.main import app

client = TestClient(app)


# =============================================================================
# 1. Source Discovery & Provider Hierarchy
# =============================================================================

def test_source_discovery():
    """Verify provider hierarchy (PRIMARY > SECONDARY > DEMO) and specifications."""
    providers = ProviderHierarchy.list_providers()
    assert len(providers) >= 5

    p_map = {p["provider_id"]: p for p in providers}
    assert "ncmrwf_ncum" in p_map
    assert "ncmrwf_neps" in p_map
    assert "imd_obs" in p_map
    assert "gfs" in p_map
    assert "gefs" in p_map

    # Primary tier checks
    assert p_map["ncmrwf_ncum"]["tier"] == "PRIMARY"
    assert p_map["ncmrwf_ncum"]["is_operational_primary"] is True
    assert p_map["ncmrwf_ncum"]["native_resolution_deg"] == 0.12
    assert p_map["ncmrwf_ncum"]["canonical_resolution_deg"] == 0.25

    # Secondary tier checks
    assert p_map["gfs"]["tier"] == "SECONDARY"
    assert p_map["gfs"]["is_operational_primary"] is False


# =============================================================================
# 2. Real vs Synthetic Classification
# =============================================================================

def test_real_synthetic_classification():
    """Verify anti-mislabeling: secondary proxy is NEVER labeled as NCMRWF or REAL_OPERATIONAL."""
    # Enforce proxy mode for GFS
    mode_gfs = ProviderHierarchy.validate_mode_for_provider("gfs", DataMode.REAL_OPERATIONAL)
    assert mode_gfs == DataMode.PUBLIC_PROXY  # Forced to PUBLIC_PROXY, cannot be operational

    # Enforce demo mode for synthetic generator
    mode_demo = ProviderHierarchy.validate_mode_for_provider("synthetic_demo", DataMode.REAL_OPERATIONAL)
    assert mode_demo == DataMode.SYNTHETIC_DEMO

    # Discovery service reports synthetic mode when real data files are absent
    discovery = DataDiscoveryService()
    matrix = discovery.get_availability_matrix()
    assert matrix.overall_mode in (DataMode.SYNTHETIC_DEMO.value, DataMode.REAL_OPERATIONAL.value)
    if not matrix.real_data_available:
        assert "REAL DATA NOT AVAILABLE" in matrix.honesty_notice


# =============================================================================
# 3. Forecast Cycle Discovery (No Fabrication)
# =============================================================================

def test_cycle_discovery():
    """Verify cycles are discovered accurately and never fabricated when files are absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create 3 cycle files for 2026-07-15 00Z with leads 24h, 48h, 72h
        (tmp_path / "ncum_20260715_00z_f024.nc").touch()
        (tmp_path / "ncum_20260715_00z_f048.nc").touch()
        (tmp_path / "ncum_20260715_00z_f072.nc").touch()

        files = list(tmp_path.glob("*.nc"))
        cycles = CycleManager.aggregate_cycles_from_files(
            files=files,
            model_name="NCUM",
            provider_id="ncmrwf_ncum",
            data_mode=DataMode.REAL_OPERATIONAL.value,
        )

        assert len(cycles) == 1
        c = cycles[0]
        assert c.cycle_id == "NCUM_20260715_00Z"
        assert c.date == "2026-07-15"
        assert c.cycle_utc == "00 UTC"
        assert c.cycle_hour == 0
        assert sorted(c.available_leads) == [24, 48, 72]
        assert c.status == "PARTIAL"
        assert len(c.files) == 3


# =============================================================================
# 4. Lead Time Discovery & Normalization
# =============================================================================

def test_lead_discovery():
    """Verify arbitrary lead extraction (not hardcoded to 24..120)."""
    assert LeadTimeNormalizer.extract_lead_from_filename("ncum_20260715_00z_f006.nc") == 6
    assert LeadTimeNormalizer.extract_lead_from_filename("ncum_20260715_00z_f018.nc") == 18
    assert LeadTimeNormalizer.extract_lead_from_filename("ncum_20260715_00z_f168.nc") == 168
    assert LeadTimeNormalizer.extract_lead_from_filename("gfs_lead48.nc") == 48
    assert LeadTimeNormalizer.extract_lead_from_filename("gfs_72hr.grib2") == 72

    assert LeadTimeNormalizer.format_lead_tag(6) == "6h"
    assert LeadTimeNormalizer.format_lead_tag(168) == "168h"


# =============================================================================
# 5. Coordinate Detection (Lat, Lon, Time, Ordering)
# =============================================================================

def test_coordinate_detection():
    """Verify coordinate discovery, resolution detection, and ordering inspection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "test_coords.nc"

        lats = np.linspace(8.0, 37.0, 100) # ~0.29 deg
        lons = np.linspace(68.0, 97.0, 100)
        times = [np.datetime64("2026-07-15T00:00:00")]
        data = np.random.uniform(0, 50, size=(1, 100, 100))

        ds = xr.Dataset(
            {"total_precipitation": (["time", "lat", "lon"], data)},
            coords={"time": times, "lat": lats, "lon": lons},
            attrs={"Conventions": "CF-1.6", "title": "Test NCUM Output"},
        )
        ds["lat"].attrs["units"] = "degrees_north"
        ds["lon"].attrs["units"] = "degrees_east"
        ds["total_precipitation"].attrs["units"] = "kg/m^2"
        ds.to_netcdf(fpath)

        report = CFMetadataInspector.inspect(fpath)
        assert report.is_valid is True
        assert report.conventions == "CF-1.6"
        assert report.coordinates["lat"] == "lat"
        assert report.coordinates["lon"] == "lon"
        assert report.latitude_info["order"] == "ascending"
        assert report.latitude_info["size"] == 100
        assert report.longitude_info["size"] == 100
        assert report.discovered_canonical_variables == ["precip_nwp_raw"]


# =============================================================================
# 6. Unit Detection & Metadata Verification
# =============================================================================

def test_unit_detection():
    """Verify units are read directly from file metadata and not hardcoded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "test_units.nc"

        lats = np.array([10.0, 11.0])
        lons = np.array([75.0, 76.0])
        times = [np.datetime64("2026-07-15T00:00:00")]

        ds = xr.Dataset(
            {
                "air_temperature_850hPa": (["time", "lat", "lon"], np.array([[[295.15, 296.15], [294.15, 295.85]]])),
                "air_pressure_at_sea_level": (["time", "lat", "lon"], np.array([[[100800.0, 100750.0], [100820.0, 100790.0]]])),
            },
            coords={"time": times, "lat": lats, "lon": lons},
        )
        ds["air_temperature_850hPa"].attrs["units"] = "K"
        ds["air_pressure_at_sea_level"].attrs["units"] = "Pa"
        ds.to_netcdf(fpath)

        report = CFMetadataInspector.inspect(fpath)
        assert report.variables["air_temperature_850hPa"].units == "K"
        assert report.variables["air_pressure_at_sea_level"].units == "Pa"
        assert "t850" in report.discovered_canonical_variables
        assert "mslp" in report.discovered_canonical_variables


# =============================================================================
# 7. Timestamp Matching & Anti-Leakage Guard
# =============================================================================

def test_timestamp_matching_and_anti_leakage():
    """Verify matching contract: forecast_valid_time == observation_time and anti-leakage."""
    init_time = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    lead_hours = 24
    valid_time = init_time + timedelta(hours=lead_hours) # 2026-07-16 00:00:00 UTC

    # Case A: Exact match
    res_match = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_time,
        lead_time_hours=lead_hours,
        observation_time=valid_time,
    )
    assert res_match.status == MatchStatus.MATCHED
    assert res_match.is_temporally_valid is True
    assert res_match.leakage_violation is False

    # Case B: Misaligned by 12 hours
    misaligned_time = valid_time + timedelta(hours=12)
    res_misalign = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_time,
        lead_time_hours=lead_hours,
        observation_time=misaligned_time,
    )
    assert res_misalign.status == MatchStatus.MISALIGNED
    assert res_misalign.leakage_violation is True


# =============================================================================
# 8. Missing Observation Handling (Zero-Fill Prohibition)
# =============================================================================

def test_missing_observation_handling():
    """Verify missing observations return MISSING_OBSERVATION and are NEVER converted to 0 mm."""
    init_time = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)

    # Missing observation
    res = DataMatchingEngine.match_forecast_to_observation(
        initialization_time=init_time,
        lead_time_hours=24,
        observation_time=None,
        obs_grid_present=False,
    )
    assert res.status == MatchStatus.MISSING_OBSERVATION
    assert "NEVER converted into 0 mm" in (res.error_message or "")


# =============================================================================
# 9. Duplicate Timestamp Detection
# =============================================================================

def test_duplicate_timestamp_detection():
    """Verify that duplicate timestamps in a dataset time dimension are flagged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "dup_times.nc"
        # Duplicate times
        times = [
            np.datetime64("2026-07-15T00:00:00"),
            np.datetime64("2026-07-15T00:00:00"), # Duplicate
            np.datetime64("2026-07-16T00:00:00"),
        ]
        data = np.zeros((3, 2, 2))
        ds = xr.Dataset(
            {"rf": (["time", "lat", "lon"], data)},
            coords={"time": times, "lat": [10.0, 11.0], "lon": [75.0, 76.0]},
        )
        ds.to_netcdf(fpath)

        report = CFMetadataInspector.inspect(fpath)
        assert report.duplicate_timestamps == 1


# =============================================================================
# 10. Corrupted File Quarantine & Graceful Handling
# =============================================================================

def test_corrupted_file_handling():
    """Verify corrupted files are quarantined with clear error and do NOT crash the service."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_path = Path(tmpdir) / "corrupt_model.nc"
        # Write 256 bytes of garbage
        with open(corrupt_path, "wb") as f:
            f.write(b"NOT_A_NETCDF_HEADER_GARBAGE_BYTES" * 8)

        report = CFMetadataInspector.inspect(corrupt_path)
        assert report.is_corrupted is True
        assert report.is_valid is False
        assert "Corrupted or unreadable NetCDF" in (report.error or "")
        assert report.checksum_sha256 != ""


# =============================================================================
# 11. Checksum (SHA-256) Calculation
# =============================================================================

def test_checksum_computation():
    """Verify SHA-256 checksum exactly matches file content hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "checksum_test.nc"
        content = b"RAMP_METEOROLOGY_TEST_CHECKSUM_DATA_12345"
        with open(test_file, "wb") as f:
            f.write(content)

        expected_hash = hashlib.sha256(content).hexdigest()
        computed_hash = CFMetadataInspector.compute_sha256(test_file)
        assert computed_hash == expected_hash


# =============================================================================
# 12. Native NCMRWF Grid (0.12°) to Canonical RAMP Grid (0.25°) Regridding
# =============================================================================

def test_native_to_ramp_regridding():
    """Verify regridding preserves native resolution metadata and produces canonical 0.25° grid."""
    # Synthetic ~0.12° native grid over India (e.g. 15.0 to 25.0 N, 72.0 to 82.0 E)
    native_lats = np.arange(10.0, 30.0 + 0.12 / 2, 0.12)
    native_lons = np.arange(70.0, 90.0 + 0.12 / 2, 0.12)

    # Generate synthetic rainfall field with an extreme event (> 204.5 mm)
    native_rain = np.full((len(native_lats), len(native_lons)), 25.0)
    native_rain[20:25, 20:25] = 220.0  # Extreme cell

    regridded, meta = NCMRWFGridHarmoniser.regrid_to_canonical(
        data=native_rain,
        src_lats=native_lats,
        src_lons=native_lons,
        source_model="NCUM",
        variable_name="precip_nwp_raw",
        native_resolution=0.12,
    )

    # Output must have canonical RAMP dimensions (129 lats x 137 lons over 6.5-38.5N, 66.5-100.5E)
    assert regridded.shape == (129, 137)
    assert meta.native_resolution_deg == 0.12
    assert meta.ramp_resolution_deg == 0.25
    assert meta.source_model == "NCUM"
    assert "NOT the native NCMRWF model resolution" in meta.notice

    # Rainfall must remain non-negative
    valid_cells = regridded[~np.isnan(regridded)]
    assert np.all(valid_cells >= 0.0)


# =============================================================================
# 13. Operational API Contracts Check
# =============================================================================

def test_api_operational_endpoints():
    """Verify all 8 Phase 11 operational data plane endpoints respond with standard envelopes."""
    endpoints = [
        "/api/data/sources",
        "/api/data/cycles",
        "/api/data/availability",
        "/api/data/forecast",
        "/api/data/observations",
        "/api/data/match",
        "/api/data/provenance",
        "/api/data/quality",
    ]

    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"Endpoint {ep} failed with {resp.status_code}"
        data = resp.json()
        assert "data_mode" in data
        assert "source" in data
        assert "timestamp" in data
        assert "provenance" in data
        assert "availability_status" in data
        assert "data" in data
