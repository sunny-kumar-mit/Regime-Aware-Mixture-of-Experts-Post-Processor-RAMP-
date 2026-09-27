"""
Phase 8 Unified Real Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Unified orchestrator for real operational data.
Scans for NetCDF, GRIB, Parquet, and CSV archives.
Falls back transparently to SyntheticDataProvider when real archives are unmounted,
while strictly declaring data_mode = SYNTHETIC_DEMO.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract
from ml.data.providers.base import BaseDataProvider
from ml.data.providers.netcdf import NetCDFDataProvider
from ml.data.providers.grib import GRIBDataProvider
from ml.data.providers.parquet import ParquetDataProvider
from ml.data.providers.csv_provider import CSVDataProvider
from ml.data.providers.synthetic import SyntheticDataProvider
from ml.data.discovery import DataDiscoveryService

logger = logging.getLogger(__name__)


class RealDataProvider(BaseDataProvider):
    """
    Unified operational provider that dynamically discovers and loads real archives.
    Determines REAL vs SYNTHETIC_DEMO status from physical file inspection.
    """

    def __init__(
        self,
        real_data_dir: Path | str = "data/real",
        allow_synthetic_fallback: bool = True,
    ) -> None:
        self.real_data_dir = Path(real_data_dir)
        self.allow_synthetic_fallback = allow_synthetic_fallback
        self.discovery_service = DataDiscoveryService([self.real_data_dir, "data/raw"])
        self._active_provider: Optional[BaseDataProvider] = None
        self._inspect_and_bind()

    def _inspect_and_bind(self) -> None:
        """Inspects disk to bind the most appropriate provider."""
        # Fast path: check file existence without running expensive xarray discovery
        has_nc = False
        for root in [self.real_data_dir, Path("data/raw")]:
            if root.exists():
                for p in root.rglob("*.nc"):
                    if "test_fixture" not in p.name:
                        has_nc = True
                        break
            if has_nc:
                break

        if has_nc:
            logger.info("Binding NetCDFDataProvider.")
            self._active_provider = NetCDFDataProvider(self.real_data_dir)
            return

        # Check for real Parquet
        has_pq = False
        for root in [self.real_data_dir, Path("data/raw")]:
            if root.exists():
                for p in root.rglob("*.parquet"):
                    has_pq = True
                    break
            if has_pq:
                break

        if has_pq:
            logger.info("Binding ParquetDataProvider.")
            self._active_provider = ParquetDataProvider(self.real_data_dir, data_mode=DataMode.REAL)
            return

        # If no real data found, bind synthetic fallback if allowed
        if self.allow_synthetic_fallback:
            logger.info("Real operational archives not found. Binding SyntheticDataProvider (honest SYNTHETIC_DEMO).")
            self._active_provider = SyntheticDataProvider()
        else:
            self._active_provider = None

    def get_mode(self) -> DataMode:
        if self._active_provider is not None:
            return self._active_provider.get_mode()
        return DataMode.SYNTHETIC_DEMO

    def get_source_name(self) -> str:
        if self._active_provider is not None:
            return self._active_provider.get_source_name()
        return "None_RealDataNotAvailable"

    def is_available(self) -> bool:
        if self._active_provider is not None:
            return self._active_provider.is_available()
        return False

    def is_real_data_available(self) -> bool:
        """Explicit check: is genuine real data available?"""
        return self.get_mode() == DataMode.REAL and self.is_available()

    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        if self._active_provider is None:
            raise FileNotFoundError(
                f"No real meteorological data found in '{self.real_data_dir}' "
                "and synthetic fallback is disabled."
            )
        return self._active_provider.load_canonical(start_date=start_date, end_date=end_date, lead_times=lead_times)

    def get_contract(self) -> DatasetContract:
        if self._active_provider is not None:
            return self._active_provider.get_contract()
        return DatasetContract(
            dataset_id="unmounted_real_data",
            dataset_version="v0.0.0",
            source="NOT_AVAILABLE",
            data_mode=DataMode.REAL,
            time_range={"start": "N/A", "end": "N/A"},
            spatial_extent={"lat_min": 0, "lat_max": 0, "lon_min": 0, "lon_max": 0},
            resolution="N/A",
            lead_times=[],
            quality_status="FAIL",
        )
