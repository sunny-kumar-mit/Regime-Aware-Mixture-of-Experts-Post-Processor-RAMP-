"""
RAMP District & State Spatial Forecast Products Schema
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class DistrictForecastProduct:
    """
    Standardized operational district forecast product (28 required fields + diagnostics).
    """
    product_id: str
    district_id: str
    district_name: str
    state_id: str
    state_name: str
    forecast_valid_time: str
    initialization_time: str
    lead_time_hours: int
    aggregation_method: str
    rainfall_mm: float
    min_rainfall_mm: float
    max_rainfall_mm: float
    median_rainfall_mm: float
    p90_rainfall_mm: float
    p95_rainfall_mm: float
    p99_rainfall_mm: float
    rain_probability: float
    heavy_probability: float
    very_heavy_probability: float
    extreme_probability: float
    hotspot_latitude: float
    hotspot_longitude: float
    hotspot_rainfall_mm: float
    valid_grid_cells: int
    total_grid_cells: int
    coverage_fraction: float
    regime_distribution: Dict[str, float]
    uncertainty: Dict[str, Any]
    model_version: str
    dataset_version: str
    data_mode: str
    boundary_version: str

    # Additional operational and diagnostic attributes
    raw_nwp_rainfall_mm: float = 0.0
    global_ml_rainfall_mm: float = 0.0
    difference_nwp_mm: float = 0.0
    difference_global_ml_mm: float = 0.0
    risk_category: str = "NORMAL"
    risk_description: str = "Normal monsoon conditions"
    color_hex: str = "#009933"
    hotspot_intensity: float = 1.0
    max_heavy_probability: float = 0.0
    max_extreme_probability: float = 0.0
    high_risk_cells_count: int = 0
    area_km2: float = 0.0
    classification_rule: str = "DEFAULT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateForecastProduct:
    """
    Aggregated state-level forecast summary.
    """
    state_id: str
    state_name: str
    forecast_valid_time: str
    lead_time_hours: int
    district_count: int
    total_area_km2: float
    area_weighted_rainfall_mm: float
    max_district_rainfall_mm: float
    max_rainfall_district: str
    mean_rainfall_mm: float
    high_risk_districts: int
    very_high_risk_districts: int
    extreme_risk_districts: int
    mean_heavy_probability: float
    mean_extreme_probability: float
    districts: List[Dict[str, Any]] = field(default_factory=list)
    data_mode: str = "SYNTHETIC_DEMO"
    model_version: str = "ramp_v1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NationalForecastSummary:
    """
    All-India national executive forecast bulletin.
    """
    forecast_valid_time: str
    lead_time_hours: int
    data_mode: str
    model_version: str
    boundary_version: str
    total_districts_evaluated: int
    total_states_evaluated: int
    valid_grid_cells: int
    overall_coverage_pct: float
    districts_with_heavy_probability: int
    districts_with_very_heavy_probability: int
    districts_with_extreme_probability: int
    max_predicted_district_rainfall_mm: float
    max_rainfall_district_name: str
    max_rainfall_state_name: str
    highest_risk_spatial_region: str
    risk_category_counts: Dict[str, int]
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
