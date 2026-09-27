"""
Phase 16 Synthetic Test Fixture Generator
SIH26080 | Real-Data Activation Pipeline Testing
MoES / NCMRWF

Generates small, controlled NetCDF and tabular test fixtures for validating:
  - Ingestion mechanics
  - Integrity validation
  - Metadata parsing
  - Temporal consistency
  - Spatial bounds
  - Meteorological QC
  - Anti-leakage forecast/observation pairing

CRITICAL SCIENTIFIC INTEGRITY RULE:
  All generated fixtures carry authority_level="TEST_FIXTURE" and
  data_mode="TEST_FIXTURE". They must NEVER be classified as REAL_OPERATIONAL.
"""

import os
from pathlib import Path
import numpy as np
import netCDF4 as nc

FIXTURE_DIR = Path("tests/fixtures/phase16")
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def create_ncum_fixture():
    fpath = FIXTURE_DIR / "ncum_test_fixture_20260927_00Z_t24.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.title = "NCUM Test Fixture (Non-Operational)"
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

    # Add all 18 canonical predictors
    rng = np.random.RandomState(42)

    var_configs = {
        "precip_nwp_raw": ("mm", (0.0, 120.0)),
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


def create_neps_fixture():
    fpath = FIXTURE_DIR / "neps_test_fixture_20260927_00Z_t24.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "NCMRWF"
    ds.title = "NEPS Ensemble Test Fixture (Non-Operational)"
    ds.authority_level = "TEST_FIXTURE"
    ds.data_mode = "TEST_FIXTURE"
    ds.initialization_time = "2026-09-27T00:00:00Z"
    ds.valid_time = "2026-09-28T00:00:00Z"
    ds.lead_time_hours = 24
    ds.cycle = "00Z"

    ds.createDimension("ensemble_member", 23)
    ds.createDimension("lat", 129)
    ds.createDimension("lon", 137)

    v = ds.createVariable("precip_nwp_ensemble_member", "f4", ("ensemble_member", "lat", "lon"))
    v.units = "mm"
    rng = np.random.RandomState(43)
    v[:] = rng.uniform(0.0, 100.0, size=(23, 129, 137)).astype(np.float32)

    ds.close()
    return fpath


def create_imd_obs_fixture():
    fpath = FIXTURE_DIR / "imd_obs_test_fixture_20260928.nc"
    if fpath.exists():
        return fpath

    ds = nc.Dataset(fpath, "w", format="NETCDF4")
    ds.institution = "IMD"
    ds.title = "IMD 0.25 Gridded Rainfall Test Fixture (Non-Operational)"
    ds.authority_level = "TEST_FIXTURE"
    ds.data_mode = "TEST_FIXTURE"
    ds.observation_date = "2026-09-28"
    ds.valid_time = "2026-09-28T00:00:00Z"

    ds.createDimension("lat", 129)
    ds.createDimension("lon", 137)

    lats = np.linspace(6.5, 38.5, 129)
    lons = np.linspace(66.5, 100.5, 137)
    lat_v = ds.createVariable("lat", "f4", ("lat",))
    lat_v.units = "deg_N"
    lat_v[:] = lats
    lon_v = ds.createVariable("lon", "f4", ("lon",))
    lon_v.units = "deg_E"
    lon_v[:] = lons

    rf = ds.createVariable("observed_rainfall_mm", "f4", ("lat", "lon"))
    rf.units = "mm"
    rng = np.random.RandomState(44)
    rf[:] = rng.exponential(scale=15.0, size=(129, 137)).astype(np.float32)

    ds.close()
    return fpath


def create_faulty_fixtures():
    # 1. Zero byte file
    zpath = FIXTURE_DIR / "corrupt_zero_byte.nc"
    zpath.write_bytes(b"")

    # 2. Negative rain file
    npath = FIXTURE_DIR / "faulty_negative_rainfall.nc"
    ds = nc.Dataset(npath, "w", format="NETCDF4")
    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)
    v = ds.createVariable("precip_nwp_raw", "f4", ("lat", "lon"))
    v.units = "mm"
    v[:] = -25.0 * np.ones((10, 10), dtype=np.float32)
    ds.close()

    # 3. Incomplete predictors file
    ipath = FIXTURE_DIR / "incomplete_predictors.nc"
    ds = nc.Dataset(ipath, "w", format="NETCDF4")
    ds.createDimension("lat", 10)
    ds.createDimension("lon", 10)
    v = ds.createVariable("precip_nwp_raw", "f4", ("lat", "lon"))
    v.units = "mm"
    v[:] = np.ones((10, 10), dtype=np.float32)
    ds.close()


if __name__ == "__main__":
    print("Generating Phase 16 test fixtures...")
    p1 = create_ncum_fixture()
    print(f"Created: {p1}")
    p2 = create_neps_fixture()
    print(f"Created: {p2}")
    p3 = create_imd_obs_fixture()
    print(f"Created: {p3}")
    create_faulty_fixtures()
    print("Faulty fixtures created.")
    print("All fixtures successfully generated in tests/fixtures/phase16/")
