"""
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
