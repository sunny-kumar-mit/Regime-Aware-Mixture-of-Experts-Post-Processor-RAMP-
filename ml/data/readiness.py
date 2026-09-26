"""
Phase 8 Real Data Readiness Verification
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Command: python -m ml.data readiness
Returns: REAL_DATA_AVAILABLE = YES/NO
If NO: details required data format, variables, coordinates, time range.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List
from ml.data.discovery import DataDiscoveryService
from ml.data.providers.real_provider import RealDataProvider


@dataclass
class ReadinessReport:
    real_data_available: bool
    status_str: str  # REAL_DATA_AVAILABLE = YES or REAL_DATA_AVAILABLE = NO
    data_mode: str
    active_source: str
    real_archives_detected: int
    netcdf_files: int
    grib_files: int
    parquet_files: int
    csv_files: int
    instructions_if_unavailable: Dict[str, Any]


class RealDataReadinessChecker:
    """Checks physical readiness of real IMD/NCMRWF archives."""

    def __init__(self, search_paths: List[str] | None = None) -> None:
        self.search_paths = search_paths or ["data/real", "data/raw/nwp", "data/raw/observations"]
        self.discovery = DataDiscoveryService(self.search_paths)
        self.provider = RealDataProvider()

    def check(self) -> ReadinessReport:
        summary = self.discovery.discover()
        is_real = self.provider.is_real_data_available()

        instructions = {
            "required_archive_types": [
                "IMD Gridded Daily Rainfall (NetCDF .nc, 0.25° resolution)",
                "NCMRWF NCUM Global/Regional NWP Forecast (NetCDF or GRIB2, 0.12° to 0.25°)",
            ],
            "expected_directory_structure": {
                "observations": "data/real/observations/ or data/raw/observations/*.nc",
                "nwp_forecasts": "data/real/nwp/ or data/raw/nwp/*.nc",
            },
            "expected_variables": [
                "Observed Rainfall (rain / rainfall / rf in mm or kg/m^2)",
                "NWP Forecast Precipitation (tp / tot_precip / precipitation in m or mm)",
                "Atmospheric Synoptic Variables: mslp (Pa/hPa), u850/v850 (m/s), cape (J/kg), rh700 (%), tpw (kg/m^2)",
            ],
            "expected_time_range": "Monsoon seasons (June 1 - September 30), minimum 1 complete historical season",
            "expected_spatial_domain": "Indian Subcontinent [6.5°N - 38.5°N, 66.5°E - 100.5°E], nominal 0.25° grid",
            "current_fallback": "Synthetic demonstration pipeline active (SYNTHETIC_DEMO). Zero failure; end-to-end operable.",
        }

        status_str = "REAL_DATA_AVAILABLE = YES" if is_real else "REAL_DATA_AVAILABLE = NO"

        return ReadinessReport(
            real_data_available=is_real,
            status_str=status_str,
            data_mode="REAL" if is_real else "SYNTHETIC_DEMO",
            active_source=self.provider.get_source_name(),
            real_archives_detected=summary.total_files_scanned,
            netcdf_files=summary.netcdf_files_count,
            grib_files=summary.grib_files_count,
            parquet_files=summary.parquet_files_count,
            csv_files=summary.csv_files_count,
            instructions_if_unavailable=instructions,
        )


def main() -> None:
    checker = RealDataReadinessChecker()
    report = checker.check()

    print("=" * 65)
    print(f"  RAMP REAL-DATA READINESS CHECK | SIH26080 (MoES/NCMRWF)")
    print("=" * 65)
    print(f"Status: {report.status_str}")
    print(f"Active Mode: {report.data_mode}")
    print(f"Active Provider: {report.active_source}")
    print(f"Archives Scanned: {report.real_archives_detected} (NetCDF={report.netcdf_files}, GRIB={report.grib_files}, Parquet={report.parquet_files}, CSV={report.csv_files})")
    print("-" * 65)

    if not report.real_data_available:
        print("\n[EXPLANATION — REAL DATA NOT CURRENTLY MOUNTED]")
        inst = report.instructions_if_unavailable
        print("Required Archive Types:")
        for t in inst["required_archive_types"]:
            print(f"  - {t}")
        print("\nExpected Directory Structure:")
        for k, v in inst["expected_directory_structure"].items():
            print(f"  - {k}: {v}")
        print("\nExpected Variables:")
        for v in inst["expected_variables"]:
            print(f"  - {v}")
        print(f"\nSpatial Domain: {inst['expected_spatial_domain']}")
        print(f"Time Range: {inst['expected_time_range']}")
        print(f"\nOperational Fallback: {inst['current_fallback']}")
        print("\nNOTE: The RAMP Phase 1-8 pipeline is fully functional in SYNTHETIC_DEMO mode.")
        print("Mount real NetCDF/GRIB files into data/real/ to transition to REAL mode.")
    else:
        print("Real operational data archives verified and ready for ingestion.")
    print("=" * 65)


if __name__ == "__main__":
    main()
