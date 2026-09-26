"""
Phase 8 Parquet Meteorological Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Adapter for Parquet feature stores and operational archival extracts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract
from ml.data.providers.base import BaseDataProvider

logger = logging.getLogger(__name__)


class ParquetDataProvider(BaseDataProvider):
    """
    Parquet archive provider.
    Reads tabular spatiotemporal weather records stored in Parquet format.
    """

    def __init__(
        self,
        file_or_dir_path: Path | str,
        data_mode: DataMode = DataMode.REAL,
        source_name: str = "ParquetWeatherStore",
    ) -> None:
        self.path = Path(file_or_dir_path)
        self.data_mode = data_mode
        self.source_name = source_name

    def get_mode(self) -> DataMode:
        return self.data_mode

    def get_source_name(self) -> str:
        return self.source_name

    def is_available(self) -> bool:
        if not self.path.exists():
            return False
        if self.path.is_file():
            return self.path.suffix.lower() in [".parquet", ".pq"]
        return any(self.path.glob("*.parquet")) or any(self.path.glob("*.pq"))

    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        if not self.is_available():
            raise FileNotFoundError(f"Parquet path '{self.path}' does not exist or has no Parquet files.")

        files: List[Path] = [self.path] if self.path.is_file() else list(self.path.glob("*.parquet")) + list(self.path.glob("*.pq"))
        dfs: List[pd.DataFrame] = []
        for f in files:
            df = pd.read_parquet(f)
            dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)
        # Canonical renaming if needed
        if "nwp_rainfall" in combined.columns and "nwp_rainfall_mm" not in combined.columns:
            combined["nwp_rainfall_mm"] = combined["nwp_rainfall"]
        if "observed_rainfall" in combined.columns and "observed_rainfall_mm" not in combined.columns:
            combined["observed_rainfall_mm"] = combined["observed_rainfall"]

        combined["data_mode"] = self.data_mode.value
        combined["source"] = self.source_name
        return combined

    def get_contract(self) -> DatasetContract:
        return DatasetContract(
            dataset_id=f"parquet_{self.path.stem}",
            dataset_version="v1.0.0",
            source=self.source_name,
            data_mode=self.data_mode,
            time_range={"start": "unspecified", "end": "unspecified"},
            spatial_extent={"lat_min": 6.5, "lat_max": 38.5, "lon_min": 66.5, "lon_max": 100.5},
            resolution="0.25 deg",
            lead_times=[24, 48, 72, 96, 120],
            quality_status="PENDING",
            variables=["nwp_rainfall_mm", "observed_rainfall_mm"],
        )
