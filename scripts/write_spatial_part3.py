"""Write fss.py, export.py, registry.py, __init__.py, __main__.py
"""
import os

# 1. fss.py
fss_code = '''"""
RAMP Spatial Fractions Skill Score (FSS) Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Implements neighborhood-based spatial verification (Roberts and Lean, 2008):
  FSS = 1 - (MSE / MSE_ref)
Evaluates spatial skill across 5km, 25km, 50km, 100km, 200km neighborhood radii.
Operates honestly: returns NOT_AVAILABLE or SAMPLE_LIMITED when observations are missing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter


class FractionsSkillScoreService:
    """
    Computes spatial Fractions Skill Score across spatial scales and rainfall thresholds.
    """

    # Neighborhood scale windows at 0.25° grid (~25 km cell width)
    WINDOW_SCALES = {
        "5km": 1,    # Sub-grid point (1x1 box)
        "25km": 1,   # 1x1 grid cell (~25km)
        "50km": 3,   # 3x3 window (~75km box, radius ~37km)
        "100km": 5,  # 5x5 window (~125km box)
        "200km": 9,  # 9x9 window (~225km box)
    }

    THRESHOLDS = [0.1, 64.5, 115.6, 204.5]

    @classmethod
    def compute_fss_single(
        cls,
        forecast_grid: np.ndarray,
        observation_grid: np.ndarray,
        threshold: float,
        window_size: int = 3,
    ) -> Dict[str, Any]:
        """
        Computes FSS, MSE, and MSE_ref for a 2D spatial grid (lat x lon) at given threshold.
        """
        # Ensure grids are 2D
        if forecast_grid.ndim != 2 or observation_grid.ndim != 2:
            return {
                "fss": 0.0,
                "mse": 0.0,
                "mse_ref": 0.0,
                "forecast_fraction": 0.0,
                "observed_fraction": 0.0,
                "status": "INVALID_GRID_DIMENSIONS",
            }

        # Binary event occurrence
        f_bin = (forecast_grid >= threshold).astype(float)
        o_bin = (observation_grid >= threshold).astype(float)

        # Neighborhood fractions via 2D moving box average
        f_frac = uniform_filter(f_bin, size=window_size, mode="constant", cval=0.0)
        o_frac = uniform_filter(o_bin, size=window_size, mode="constant", cval=0.0)

        mse = float(np.mean((f_frac - o_frac) ** 2))
        mse_ref = float(np.mean(f_frac ** 2 + o_frac ** 2))

        f_mean_frac = float(np.mean(f_bin))
        o_mean_frac = float(np.mean(o_bin))

        if mse_ref < 1e-9:
            # Event did not occur in either forecast or observations
            fss = 1.0 if mse < 1e-9 else 0.0
            status = "NO_EVENTS_IN_DOMAIN"
        else:
            fss = 1.0 - (mse / mse_ref)
            fss = float(np.clip(fss, 0.0, 1.0))
            status = "PASS"

        return {
            "fss": round(fss, 4),
            "mse": round(mse, 6),
            "mse_ref": round(mse_ref, 6),
            "forecast_fraction": round(f_mean_frac, 4),
            "observed_fraction": round(o_mean_frac, 4),
            "sample_count": int(forecast_grid.size),
            "status": status,
        }

    @classmethod
    def evaluate_spatial_fss(
        cls,
        df: pd.DataFrame,
        forecast_col: str = "ramp_pred",
        obs_col: str = "observed_rainfall_mm",
        lat_col: str = "latitude",
        lon_col: str = "longitude",
    ) -> Dict[str, Any]:
        """
        Pivots DataFrame into 2D grid and evaluates FSS across all scales and thresholds.
        """
        if obs_col not in df.columns or df[obs_col].isna().all():
            return {
                "status": "NOT_AVAILABLE",
                "message": "Observations not available for spatial FSS verification.",
                "fss_curves": {},
            }

        valid_df = df.dropna(subset=[forecast_col, obs_col, lat_col, lon_col])
        if len(valid_df) < 9:
            return {
                "status": "SAMPLE_LIMITED",
                "message": f"Insufficient grid samples ({len(valid_df)}) for 2D spatial filtering.",
                "fss_curves": {},
            }

        # Pivot to 2D
        try:
            piv_f = valid_df.pivot_table(index=lat_col, columns=lon_col, values=forecast_col, aggfunc="mean").values
            piv_o = valid_df.pivot_table(index=lat_col, columns=lon_col, values=obs_col, aggfunc="mean").values
            # Fill remaining NaN cells with 0.0 for uniform filter
            piv_f = np.nan_to_num(piv_f, nan=0.0)
            piv_o = np.nan_to_num(piv_o, nan=0.0)
        except Exception as e:
            return {
                "status": "PIVOT_ERROR",
                "message": f"Could not construct 2D spatial grid: {e}",
                "fss_curves": {},
            }

        curves: Dict[str, Any] = {}
        for t in cls.THRESHOLDS:
            t_key = f"{t}mm"
            curves[t_key] = {}
            for scale_name, w_size in cls.WINDOW_SCALES.items():
                res = cls.compute_fss_single(piv_f, piv_o, threshold=t, window_size=w_size)
                curves[t_key][scale_name] = res

        return {
            "status": "PASS",
            "thresholds": cls.THRESHOLDS,
            "scales": list(cls.WINDOW_SCALES.keys()),
            "fss_curves": curves,
        }
'''

# 2. export.py
export_code = '''"""
RAMP GIS Export & Artifact Generation Service
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Supports:
  - GeoJSON spatial layers (districts, probabilities, risk, grids)
  - Tabular CSV summaries
  - Parquet spatial datasets
All exports include metadata, provenance, and data mode banners.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
from shapely.geometry import mapping

from ml.spatial.boundaries import AdministrativeBoundaryProvider
from ml.spatial.products import DistrictForecastProduct, StateForecastProduct, NationalForecastSummary


class GISExportService:
    """
    Exports spatial verification grids, district predictions, and risk maps
    to standard open GIS formats (GeoJSON, CSV, Parquet).
    """

    def __init__(self, export_dir: str = "data/spatial_exports") -> None:
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export_district_forecast_geojson(
        self,
        district_products: List[DistrictForecastProduct],
        boundary_provider: AdministrativeBoundaryProvider,
        filename: str = "district_forecast.geojson",
    ) -> str:
        """
        Exports full district forecast products with geometries as GeoJSON.
        """
        features = []
        for p in district_products:
            boundary = boundary_provider.get_district(p.district_id)
            geom_dict = mapping(boundary.geometry) if boundary else None

            feat = {
                "type": "Feature",
                "properties": {
                    "product_id": p.product_id,
                    "district_id": p.district_id,
                    "district_name": p.district_name,
                    "state_id": p.state_id,
                    "state_name": p.state_name,
                    "forecast_valid_time": p.forecast_valid_time,
                    "lead_time_hours": p.lead_time_hours,
                    "aggregation_method": p.aggregation_method,
                    "rainfall_mm": p.rainfall_mm,
                    "min_rainfall_mm": p.min_rainfall_mm,
                    "max_rainfall_mm": p.max_rainfall_mm,
                    "p95_rainfall_mm": p.p95_rainfall_mm,
                    "rain_probability": p.rain_probability,
                    "heavy_probability": p.heavy_probability,
                    "very_heavy_probability": p.very_heavy_probability,
                    "extreme_probability": p.extreme_probability,
                    "hotspot_rainfall_mm": p.hotspot_rainfall_mm,
                    "hotspot_latitude": p.hotspot_latitude,
                    "hotspot_longitude": p.hotspot_longitude,
                    "coverage_fraction": p.coverage_fraction,
                    "risk_category": p.risk_category,
                    "color_hex": p.color_hex,
                    "raw_nwp_rainfall_mm": p.raw_nwp_rainfall_mm,
                    "difference_nwp_mm": p.difference_nwp_mm,
                    "data_mode": p.data_mode,
                    "model_version": p.model_version,
                    "boundary_version": p.boundary_version,
                },
                "geometry": geom_dict,
            }
            features.append(feat)

        geojson_obj = {
            "type": "FeatureCollection",
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dataset_version": district_products[0].dataset_version if district_products else "v1.0.0",
                "model_version": district_products[0].model_version if district_products else "ramp_v1.0.0",
                "boundary_version": district_products[0].boundary_version if district_products else "v1.0.0",
                "data_mode": district_products[0].data_mode if district_products else "SYNTHETIC_DEMO",
                "aggregation_method": district_products[0].aggregation_method if district_products else "AREA_WEIGHTED",
                "total_districts": len(district_products),
            },
            "features": features,
        }

        path = os.path.join(self.export_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(geojson_obj, f, indent=2)
        return path

    def export_grid_metrics_geojson(
        self,
        grid_records: List[Dict[str, Any]],
        filename: str = "grid_rmse.geojson",
        metric_key: str = "rmse",
    ) -> str:
        """
        Exports 0.25° grid verification metrics as point or box GeoJSON.
        """
        features = []
        for r in grid_records:
            lat = r["latitude"]
            lon = r["longitude"]
            half_res = 0.25 / 2.0
            box_coords = [
                [round(lon - half_res, 4), round(lat - half_res, 4)],
                [round(lon + half_res, 4), round(lat - half_res, 4)],
                [round(lon + half_res, 4), round(lat + half_res, 4)],
                [round(lon - half_res, 4), round(lat + half_res, 4)],
                [round(lon - half_res, 4), round(lat - half_res, 4)],
            ]

            feat = {
                "type": "Feature",
                "properties": {
                    "latitude": lat,
                    "longitude": lon,
                    "metric_name": metric_key,
                    "metric_value": r.get(metric_key, 0.0),
                    "sample_count": r.get("sample_count", 0),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [box_coords],
                },
            }
            features.append(feat)

        geojson_obj = {
            "type": "FeatureCollection",
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metric": metric_key,
                "grid_count": len(features),
            },
            "features": features,
        }

        path = os.path.join(self.export_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(geojson_obj, f, indent=2)
        return path

    def export_district_csv(
        self,
        district_products: List[DistrictForecastProduct],
        filename: str = "district_forecast.csv",
    ) -> str:
        """
        Exports tabular CSV representation of district products.
        """
        rows = [p.to_dict() for p in district_products]
        df = pd.DataFrame(rows)
        # Drop nested dicts for clean tabular CSV
        cols_to_drop = [c for c in ["regime_distribution", "uncertainty"] if c in df.columns]
        df_clean = df.drop(columns=cols_to_drop)
        path = os.path.join(self.export_dir, filename)
        df_clean.to_csv(path, index=False)
        return path

    def export_district_parquet(
        self,
        district_products: List[DistrictForecastProduct],
        filename: str = "district_forecast.parquet",
    ) -> str:
        """
        Exports high-performance Parquet format.
        """
        rows = [p.to_dict() for p in district_products]
        df = pd.DataFrame(rows)
        # Convert nested dicts to JSON strings for Parquet compatibility
        if "regime_distribution" in df.columns:
            df["regime_distribution"] = df["regime_distribution"].apply(json.dumps)
        if "uncertainty" in df.columns:
            df["uncertainty"] = df["uncertainty"].apply(json.dumps)
        path = os.path.join(self.export_dir, filename)
        df.to_parquet(path, index=False)
        return path
'''

# 3. registry.py
registry_code = '''"""
RAMP Spatial Product Registry & Cache Manager
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SPATIAL_PRODUCT_VERSION = "spatial_product_v1.0.0"


class SpatialProductRegistry:
    """
    Manages versioning, caching, and immutable run manifests for spatial products.
    """

    def __init__(self, audit_dir: str = "data/audit/spatial") -> None:
        self.audit_dir = audit_dir
        self.product_version = SPATIAL_PRODUCT_VERSION
        os.makedirs(self.audit_dir, exist_ok=True)
        self._cache: Dict[str, Any] = {}

    @staticmethod
    def build_cache_key(
        dataset_version: str,
        model_version: str,
        boundary_version: str,
        valid_time: str,
        lead_hours: int,
        aggregation_method: str,
    ) -> str:
        """Generates deterministic cache key."""
        clean_time = valid_time.replace(":", "").replace("-", "")
        return f"{dataset_version}_{model_version}_{boundary_version}_{clean_time}_{lead_hours}h_{aggregation_method}"

    def get_cached_product(self, cache_key: str) -> Optional[Any]:
        return self._cache.get(cache_key)

    def cache_product(self, cache_key: str, data: Any) -> None:
        self._cache[cache_key] = data

    def clear_cache(self) -> None:
        self._cache.clear()

    def record_spatial_run(
        self,
        dataset_id: str,
        dataset_version: str,
        model_version: str,
        boundary_version: str,
        lead_time_hours: int,
        valid_time: str,
        aggregation_method: str,
        total_districts: int,
        total_cells: int,
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> Dict[str, Any]:
        """
        Records an immutable spatial aggregation run manifest.
        """
        run_id = f"spatial_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        manifest = {
            "run_id": run_id,
            "product_version": self.product_version,
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "model_version": model_version,
            "boundary_version": boundary_version,
            "lead_time_hours": lead_time_hours,
            "forecast_valid_time": valid_time,
            "aggregation_method": aggregation_method,
            "total_districts_evaluated": total_districts,
            "total_grid_cells_intersected": total_cells,
            "data_mode": data_mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        path = os.path.join(self.audit_dir, f"{run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest
'''

# 4. __init__.py
init_code = '''"""
RAMP Spatial Forecast Products & District Aggregation Package
SIH26080 | MoES / NCMRWF
"""

from ml.spatial.grid import GridCell, SpatialGridEngine
from ml.spatial.boundaries import DistrictBoundary, AdministrativeBoundaryProvider
from ml.spatial.intersection import IntersectionRecord, GridDistrictIntersectionEngine
from ml.spatial.uncertainty import SpatialUncertaintyEngine
from ml.spatial.risk import DistrictRiskClassifier
from ml.spatial.aggregation import DistrictAggregationEngine
from ml.spatial.products import DistrictForecastProduct, StateForecastProduct, NationalForecastSummary
from ml.spatial.fss import FractionsSkillScoreService
from ml.spatial.export import GISExportService
from ml.spatial.registry import SpatialProductRegistry, SPATIAL_PRODUCT_VERSION
from ml.spatial.validation import SpatialValidator, SpatialValidationError

__all__ = [
    "GridCell",
    "SpatialGridEngine",
    "DistrictBoundary",
    "AdministrativeBoundaryProvider",
    "IntersectionRecord",
    "GridDistrictIntersectionEngine",
    "SpatialUncertaintyEngine",
    "DistrictRiskClassifier",
    "DistrictAggregationEngine",
    "DistrictForecastProduct",
    "StateForecastProduct",
    "NationalForecastSummary",
    "FractionsSkillScoreService",
    "GISExportService",
    "SpatialProductRegistry",
    "SPATIAL_PRODUCT_VERSION",
    "SpatialValidator",
    "SpatialValidationError",
]
'''

with open("ml/spatial/fss.py", "w", encoding="utf-8") as f:
    f.write(fss_code)
print("Wrote ml/spatial/fss.py")

with open("ml/spatial/export.py", "w", encoding="utf-8") as f:
    f.write(export_code)
print("Wrote ml/spatial/export.py")

with open("ml/spatial/registry.py", "w", encoding="utf-8") as f:
    f.write(registry_code)
print("Wrote ml/spatial/registry.py")

with open("ml/spatial/__init__.py", "w", encoding="utf-8") as f:
    f.write(init_code)
print("Wrote ml/spatial/__init__.py")
