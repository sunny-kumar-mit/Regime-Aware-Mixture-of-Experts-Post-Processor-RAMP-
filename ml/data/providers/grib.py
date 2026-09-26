"""
Phase 8 GRIB / GRIB2 Meteorological Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Adapter for GRIB/GRIB2 operational NWP files.
Safely detects presence of ecCodes and cfgrib; handles platforms without ecCodes gracefully.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract
from ml.data.providers.base import BaseDataProvider

logger = logging.getLogger(__name__)


class GRIBDataProvider(BaseDataProvider):
    """
    GRIB / GRIB2 adapter for NCMRWF Unified Model or GFS operational cycles.
    """

    def __init__(self, file_or_dir_path: Path | str, source_name: str = "NCMRWF_GRIB") -> None:
        self.path = Path(file_or_dir_path)
        self.source_name = source_name
        self._check_engine()

    def _check_engine(self) -> bool:
        try:
            import cfgrib  # noqa
            self._engine_available = True
        except Exception:
            self._engine_available = False
        return self._engine_available

    def get_mode(self) -> DataMode:
        return DataMode.REAL

    def get_source_name(self) -> str:
        return self.source_name

    def is_available(self) -> bool:
        if not self._engine_available:
            return False
        if not self.path.exists():
            return False
        if self.path.is_file():
            return self.path.suffix.lower() in [".grb", ".grib", ".grib2", ".grb2"]
        return any(self.path.glob("*.grb*")) or any(self.path.glob("*.grib*"))

    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        if not self._engine_available:
            raise RuntimeError(
                "Direct GRIB/GRIB2 reading requires the ecCodes binary and cfgrib Python package. "
                "For environments without ecCodes, please convert GRIB to NetCDF via `cdo -f nc copy in.grib out.nc` "
                "or use the NetCDFDataProvider."
            )
        if not self.is_available():
            raise FileNotFoundError(f"GRIB path '{self.path}' does not exist or has no GRIB files.")

        import xarray as xr
        logger.info(f"[GRIB] Opening {self.path} with cfgrib engine ...")
        with xr.open_dataset(self.path, engine="cfgrib") as ds:
            df = ds.to_dataframe().reset_index()
            df["data_mode"] = DataMode.REAL.value
            df["source"] = self.source_name
            return df

    def get_contract(self) -> DatasetContract:
        return DatasetContract(
            dataset_id=f"real_grib_{self.path.stem}",
            dataset_version="v1.0.0",
            source=self.source_name,
            data_mode=DataMode.REAL,
            time_range={"start": "unspecified", "end": "unspecified"},
            spatial_extent={"lat_min": 6.5, "lat_max": 38.5, "lon_min": 66.5, "lon_max": 100.5},
            resolution="0.25 deg",
            lead_times=[24, 48, 72, 96, 120],
            quality_status="PENDING",
            variables=["nwp_rainfall_mm"],
        )
