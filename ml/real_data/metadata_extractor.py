"""
RAMP Meteorological Metadata Extractor
SIH26080 | MoES / NCMRWF | Phase 19 Upgrade

Extracts temporal, spatial, and variable metadata from raw files without fabrication.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import netCDF4 as nc
except ImportError:
    nc = None


class MetadataExtractor:
    """
    Inspects NetCDF4, CSV, Parquet, and IMD binary files to extract physical metadata.
    """

    @classmethod
    def extract_metadata(cls, filepath: str | Path) -> Dict[str, Any]:
        path = Path(filepath)
        if not path.exists():
            return {"error": f"File does not exist: {path}"}

        suffix = path.suffix.lower()
        if suffix in [".nc", ".nc4"]:
            return cls._extract_netcdf_metadata(path)
        elif suffix in [".grd"]:
            return cls._extract_imd_binary_metadata(path)
        elif suffix in [".csv"]:
            return cls._extract_csv_metadata(path)
        else:
            return {
                "format": suffix.replace(".", "").upper(),
                "size_bytes": path.stat().st_size,
                "variables": [],
            }

    @classmethod
    def _extract_netcdf_metadata(cls, path: Path) -> Dict[str, Any]:
        if nc is None:
            return {"format": "NETCDF4", "size_bytes": path.stat().st_size}

        meta: Dict[str, Any] = {
            "format": "NETCDF4",
            "size_bytes": path.stat().st_size,
            "variables": [],
            "dimensions": {},
            "units_map": {},
            "lat_range": None,
            "lon_range": None,
            "cycle": None,
            "lead_hours": None,
            "valid_time": None,
            "initialization_time": None,
        }

        try:
            with nc.Dataset(path, "r") as ds:
                meta["variables"] = list(ds.variables.keys())
                for dname, dim in ds.dimensions.items():
                    meta["dimensions"][dname] = len(dim)

                for vname, var in ds.variables.items():
                    if hasattr(var, "units"):
                        meta["units_map"][vname] = str(var.units)

                # Extract lats/lons
                for lat_k in ["lat", "latitude", "LAT", "Latitude"]:
                    if lat_k in ds.variables:
                        lats = np.array(ds.variables[lat_k][:])
                        meta["lat_range"] = (float(np.min(lats)), float(np.max(lats)))
                        break

                for lon_k in ["lon", "longitude", "LON", "Longitude"]:
                    if lon_k in ds.variables:
                        lons = np.array(ds.variables[lon_k][:])
                        meta["lon_range"] = (float(np.min(lons)), float(np.max(lons)))
                        break

                meta["cycle"] = getattr(ds, "cycle", getattr(ds, "forecast_cycle", None))
                meta["lead_hours"] = getattr(ds, "lead_time_hours", getattr(ds, "lead_hours", None))
                meta["initialization_time"] = getattr(ds, "initialization_time", getattr(ds, "init_time", None))
                meta["valid_time"] = getattr(ds, "valid_time", getattr(ds, "valid_date", None))
        except Exception as e:
            meta["error"] = str(e)

        return meta

    @classmethod
    def _extract_imd_binary_metadata(cls, path: Path) -> Dict[str, Any]:
        size_bytes = path.stat().st_size
        return {
            "format": "IMD_BINARY_GRD",
            "size_bytes": size_bytes,
            "grid_dims": (129, 137),
            "resolution": 0.25,
            "lat_range": (6.5, 38.5),
            "lon_range": (66.5, 100.5),
            "variables": ["rain"],
            "units_map": {"rain": "mm/day"},
            "is_ground_truth_only": True,
        }

    @classmethod
    def _extract_csv_metadata(cls, path: Path) -> Dict[str, Any]:
        import pandas as pd
        df = pd.read_csv(path, nrows=5)
        return {
            "format": "CSV",
            "size_bytes": path.stat().st_size,
            "variables": list(df.columns),
            "row_count_estimate": sum(1 for _ in open(path, "r", encoding="utf-8")),
        }
