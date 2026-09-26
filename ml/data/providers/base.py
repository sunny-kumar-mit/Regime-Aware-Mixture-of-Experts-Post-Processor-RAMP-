"""
Phase 8 Abstract Meteorological Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd
from ml.data.contract import CanonicalRecord, DataMode, DatasetContract


class BaseDataProvider(ABC):
    """
    Abstract base class for all meteorological data providers.
    Supports pluggable formats (NetCDF, GRIB, Parquet, CSV, Synthetic).
    """

    @abstractmethod
    def get_mode(self) -> DataMode:
        """Returns DataMode.REAL or DataMode.SYNTHETIC_DEMO."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Returns the human-readable source center/system name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the actual physical data source exists and is accessible."""
        pass

    @abstractmethod
    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Loads and standardizes records into the canonical DataFrame schema.
        Must contain: latitude, longitude, initialization_time, forecast_valid_time,
        lead_time_hours, nwp_rainfall_mm, and optionally observed_rainfall_mm.
        """
        pass

    @abstractmethod
    def get_contract(self) -> DatasetContract:
        """Returns the dataset contract metadata describing this data source."""
        pass
