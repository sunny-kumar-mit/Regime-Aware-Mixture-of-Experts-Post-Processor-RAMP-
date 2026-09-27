"""
Phase 18 Controlled Test Fixture Generator
SIH26080 | Real-Data Activation & Institutional Acceptance Testing
MoES / NCMRWF

PART AR: Controlled Fixture Testing
Generates strictly labeled test fixtures with:
  dataset_type = TEST_FIXTURE
  authority_level = TEST_FIXTURE
Never presents fixture outputs as real meteorological evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    nc = None

from ml.ingestion.sources import CANONICAL_18_PREDICTORS

FIXTURE_DIR = Path("tests/fixtures/phase18")
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def create_valid_ncum_fixture() -> Path:
    fpath = FIXTURE_DIR / "ncum_valid_test_fixture.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.title = "NCUM Valid Test Fixture (Non-Operational)"
    ds.authority_level = "TEST_FIXTURE"
    ds.data_mode = "TEST_FIXTURE"
    ds.initialization_time = "2026-09-27T00:00:00Z"
    ds.valid_time = "2026-09-28T00:00:00Z"
    ds.lead_time_hours = 24
    ds.cycle = "00Z"

    # Canonical grid: 129 lats x 137 lons
    lats = np.linspace(6.5, 38.5, 129)
    lons = np.linspace(66.5, 100.5, 137)

    ds.createDimension("lat", 129)
    ds.createDimension("lon", 137)

    lat_var = ds.createVariable("lat", "f4", ("lat",))
    lat_var.units = "deg_N"
    lat_var[:] = lats

    lon_var = ds.createVariable("lon", "f4", ("lon",))
    lon_var.units = "deg_E"
    lon_var[:] = lons

    rng = np.random.RandomState(42)

    var_configs = {
        "precip_nwp_raw": ("mm", (0.0, 150.0)),
        "u850": ("m/s", (-15.0, 25.0)),
        "v850": ("m/s", (-10.0, 20.0)),
        "mslp": ("hPa", (995.0, 1015.0)),
        "t850": ("K", (280.0, 305.0)),
        "cape": ("J/kg", (100.0, 3500.0)),
        "wind_speed_850": ("m/s", (2.0, 30.0)),
        "wind_dir_850": ("deg", (0.0, 360.0)),
        "lead_time_hours": ("hours", (24.0, 24.0)),
        "latitude": ("deg_N", (6.5, 38.5)),
        "longitude": ("deg_E", (66.5, 100.5)),
        "elevation_m": ("m", (0.0, 3000.0)),
        "day_of_year_sin": ("dimensionless", (-1.0, 1.0)),
        "day_of_year_cos": ("dimensionless", (-1.0, 1.0)),
        "zonal_shear": ("m/s", (-10.0, 15.0)),
        "monsoon_trough_intensity": ("hPa", (-10.0, 10.0)),
        "meridional_flow": ("m/s", (-8.0, 12.0)),
        "humidity_proxy": ("dimensionless", (0.3, 0.95)),
    }

    for vname, (unit, (low, high)) in var_configs.items():
        v = ds.createVariable(vname, "f4", ("lat", "lon"))
        v.units = unit
        v[:] = rng.uniform(low, high, size=(129, 137)).astype(np.float32)

    ds.close()
    return fpath


def create_invalid_ncum_missing_predictors() -> Path:
    fpath = FIXTURE_DIR / "ncum_invalid_missing_predictors.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.authority_level = "TEST_FIXTURE"
    ds.initialization_time = "2026-09-27T00:00:00Z"
    ds.valid_time = "2026-09-28T00:00:00Z"
    ds.cycle = "00Z"
    ds.lead_time_hours = 24

    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)

    # Only 2 predictors instead of 18
    p = ds.createVariable("precip_nwp_raw", "f4", ("lat", "lon"))
    p.units = "mm"
    p[:] = np.ones((10, 10), dtype=np.float32) * 10.0

    t = ds.createVariable("t850", "f4", ("lat", "lon"))
    t.units = "K"
    t[:] = np.ones((10, 10), dtype=np.float32) * 295.0

    ds.close()
    return fpath


def create_valid_neps_fixture() -> Path:
    fpath = FIXTURE_DIR / "neps_valid_23_members.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.title = "NEPS 23-Member Valid Ensemble (Test Fixture)"
    ds.authority_level = "TEST_FIXTURE"
    ds.cycle = "00Z"
    ds.lead_time_hours = 24

    ds.createDimension("lat", 30)
    ds.createDimension("lon", 30)

    rng = np.random.RandomState(42)
    for i in range(23):
        m = ds.createVariable(f"ens{i:02d}", "f4", ("lat", "lon"))
        m.units = "mm"
        m[:] = rng.uniform(0.0, 80.0, size=(30, 30)).astype(np.float32)

    ds.close()
    return fpath


def create_missing_neps_fixture() -> Path:
    fpath = FIXTURE_DIR / "neps_missing_members.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.title = "NEPS Incomplete Ensemble (20 Members)"
    ds.authority_level = "TEST_FIXTURE"
    ds.cycle = "00Z"
    ds.lead_time_hours = 24

    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)

    rng = np.random.RandomState(42)
    # Only 20 members (missing ens20, ens21, ens22)
    for i in range(20):
        m = ds.createVariable(f"ens{i:02d}", "f4", ("lat", "lon"))
        m.units = "mm"
        m[:] = rng.uniform(0.0, 50.0, size=(10, 10)).astype(np.float32)

    ds.close()
    return fpath


def create_valid_imd_fixture() -> Path:
    fpath = FIXTURE_DIR / "imd_valid_025_grid.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "IMD"
    ds.title = "IMD Gridded Rainfall Test Fixture"
    ds.authority_level = "TEST_FIXTURE"
    ds.valid_date = "2026-09-28"

    lats = np.linspace(6.5, 38.5, 129)
    lons = np.linspace(66.5, 100.5, 137)

    ds.createDimension("lat", 129)
    ds.createDimension("lon", 137)

    lat_var = ds.createVariable("lat", "f4", ("lat",))
    lat_var.units = "deg_N"
    lat_var[:] = lats

    lon_var = ds.createVariable("lon", "f4", ("lon",))
    lon_var.units = "deg_E"
    lon_var[:] = lons

    rain = ds.createVariable("observed_rainfall_mm", "f4", ("lat", "lon"))
    rain.units = "mm"
    rng = np.random.RandomState(42)
    rain[:] = rng.uniform(0.0, 120.0, size=(129, 137)).astype(np.float32)

    ds.close()
    return fpath


def create_invalid_imd_fixture() -> Path:
    fpath = FIXTURE_DIR / "imd_invalid_negative_rain.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "IMD"
    ds.authority_level = "TEST_FIXTURE"
    ds.valid_date = "2026-09-28"

    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)

    rain = ds.createVariable("observed_rainfall_mm", "f4", ("lat", "lon"))
    rain.units = "mm"
    arr = np.ones((10, 10), dtype=np.float32) * 20.0
    arr[2, 2] = -50.0  # Violation: negative rainfall
    rain[:] = arr

    ds.close()
    return fpath


def create_bad_coordinates_fixture() -> Path:
    fpath = FIXTURE_DIR / "ncum_bad_coordinates.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.authority_level = "TEST_FIXTURE"
    ds.initialization_time = "2026-09-27T00:00:00Z"
    ds.valid_time = "2026-09-28T00:00:00Z"
    ds.cycle = "00Z"
    ds.lead_time_hours = 24

    # Out of canonical domain: 50N to 70N
    lats = np.linspace(50.0, 70.0, 10)
    lons = np.linspace(10.0, 30.0, 10)

    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)

    lat_var = ds.createVariable("lat", "f4", ("lat",))
    lat_var[:] = lats

    lon_var = ds.createVariable("lon", "f4", ("lon",))
    lon_var[:] = lons

    for vname in CANONICAL_18_PREDICTORS:
        v = ds.createVariable(vname, "f4", ("lat", "lon"))
        v[:] = np.ones((10, 10), dtype=np.float32) * 5.0

    ds.close()
    return fpath


def generate_all_phase18_fixtures():
    create_valid_ncum_fixture()
    create_invalid_ncum_missing_predictors()
    create_valid_neps_fixture()
    create_missing_neps_fixture()
    create_valid_imd_fixture()
    create_invalid_imd_fixture()
    create_bad_coordinates_fixture()


if __name__ == "__main__":
    generate_all_phase18_fixtures()
    print("All Phase 18 test fixtures successfully generated.")
