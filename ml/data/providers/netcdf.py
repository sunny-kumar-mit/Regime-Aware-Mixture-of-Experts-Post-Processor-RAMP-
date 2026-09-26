"""
Phase 8 NetCDF Meteorological Data Provider
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Adapter for NetCDF3/NetCDF4 archives (IMD gridded rainfall, NCMRWF NCUM, ECMWF ERA5/IFS).
Uses xarray for multidimensional array ingestion.
Normalizes units and standardizes coordinates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.data.contract import CanonicalRecord, DataMode, DatasetContract
from ml.data.providers.base import BaseDataProvider
from ml.data.units import UnitNormalizer
from ml.data.alignment import SpatialAlignmentEngine

logger = logging.getLogger(__name__)


class NetCDFDataProvider(BaseDataProvider):
    """
    NetCDF file and directory provider.
    Reads CF-compliant and IMD/NCMRWF NetCDF files and extracts canonical records.
    """

    DEFAULT_VAR_MAPPINGS = {
        "rain": "observed_rainfall_mm",
        "rainfall": "observed_rainfall_mm",
        "rf": "observed_rainfall_mm",
        "precip": "observed_rainfall_mm",
        "precipitation": "observed_rainfall_mm",
        "tp": "nwp_rainfall_mm",
        "tot_precip": "nwp_rainfall_mm",
        "nwp_rain": "nwp_rainfall_mm",
        "mslp": "mslp_pa",
        "prmsl": "mslp_pa",
        "u850": "u850_ms",
        "v850": "v850_ms",
        "cape": "cape_jkg",
        "rh700": "rh700_pct",
        "r700": "rh700_pct",
        "tpw": "tpw_kgm2",
        "tcwv": "tpw_kgm2",
        "t2m": "temp2m_k",
        "temp2m": "temp2m_k",
        "gh500": "gh500_m",
        "z500": "gh500_m",
    }

    def __init__(
        self,
        file_or_dir_path: Path | str,
        is_observation: bool = False,
        source_name: str = "IMD_NCMRWF_NetCDF",
    ) -> None:
        self.path = Path(file_or_dir_path)
        self.is_observation = is_observation
        self.source_name = source_name
        self.unit_normalizer = UnitNormalizer()
        self.spatial_engine = SpatialAlignmentEngine()

    def get_mode(self) -> DataMode:
        return DataMode.REAL

    def get_source_name(self) -> str:
        return self.source_name

    def is_available(self) -> bool:
        if not self.path.exists():
            return False
        if self.path.is_file():
            return self.path.suffix.lower() in [".nc", ".nc4", ".netcdf"]
        # Directory check
        return any(self.path.glob("*.nc")) or any(self.path.glob("*.nc4"))

    def load_canonical(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lead_times: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Loads and parses NetCDF file(s) into canonical DataFrame."""
        if not self.is_available():
            raise FileNotFoundError(f"NetCDF path '{self.path}' does not exist or contains no NetCDF files.")

        try:
            import xarray as xr
        except ImportError:
            raise ImportError("xarray is required for NetCDFDataProvider. Install with `pip install xarray netCDF4`.")

        files: List[Path] = [self.path] if self.path.is_file() else list(self.path.glob("*.nc")) + list(self.path.glob("*.nc4"))
        dfs: List[pd.DataFrame] = []

        for f in files:
            logger.info(f"[NetCDF] Ingesting {f.name} ...")
            with xr.open_dataset(f) as ds:
                # Coordinate resolution
                lat_key = next((k for k in ["lat", "latitude", "LAT"] if k in ds.coords), None)
                lon_key = next((k for k in ["lon", "longitude", "LON"] if k in ds.coords), None)
                time_key = next((k for k in ["time", "valid_time", "date"] if k in ds.coords), None)

                if not lat_key or not lon_key:
                    logger.warning(f"Skipping {f.name}: missing latitude/longitude coordinates.")
                    continue

                # Filter time if provided
                sub_ds = ds
                if time_key and start_date:
                    sub_ds = sub_ds.sel({time_key: slice(start_date, end_date)})

                df_ds = sub_ds.to_dataframe().reset_index()

                # Rename coordinates to canonical
                rename_map = {lat_key: "latitude", lon_key: "longitude"}
                if time_key:
                    rename_map[time_key] = "forecast_valid_time" if not self.is_observation else "observation_valid_time"

                # Rename variables to canonical
                for var in sub_ds.data_vars.keys():
                    lower_var = str(var).lower()
                    if lower_var in self.DEFAULT_VAR_MAPPINGS:
                        target_col = self.DEFAULT_VAR_MAPPINGS[lower_var]
                        rename_map[var] = target_col
                        # Check units and normalize
                        units = str(sub_ds[var].attrs.get("units", "")).lower()
                        if target_col in ["nwp_rainfall_mm", "observed_rainfall_mm"] and units:
                            if "m" in units and "mm" not in units and "kg" not in units:
                                df_ds[var] = self.unit_normalizer.normalize_precipitation_to_mm(
                                    df_ds[var].values, source_unit=units, variable_name=target_col
                                )

                df_ds.rename(columns=rename_map, inplace=True)
                df_ds["data_mode"] = DataMode.REAL.value
                df_ds["source"] = self.source_name
                df_ds["dataset_id"] = f"real_netcdf_{f.stem}"
                df_ds["dataset_version"] = "v1.0.0"

                # Snap coordinates to canonical grid
                df_ds = self.spatial_engine.snap_dataframe_to_grid(df_ds)
                dfs.append(df_ds)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)
        return combined

    def get_contract(self) -> DatasetContract:
        return DatasetContract(
            dataset_id=f"real_netcdf_{self.path.stem}",
            dataset_version="v1.0.0",
            source=self.source_name,
            data_mode=DataMode.REAL,
            time_range={"start": "unspecified", "end": "unspecified"},
            spatial_extent={"lat_min": 6.5, "lat_max": 38.5, "lon_min": 66.5, "lon_max": 100.5},
            resolution="0.25 deg",
            lead_times=[24, 48, 72, 96, 120],
            quality_status="PENDING",
            variables=list(self.DEFAULT_VAR_MAPPINGS.values()),
        )
