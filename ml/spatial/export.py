"""
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
