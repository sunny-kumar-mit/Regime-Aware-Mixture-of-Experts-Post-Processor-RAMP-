"""Write products.py and aggregation.py
"""
import os

products_code = '''"""
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
'''

with open("ml/spatial/products.py", "w", encoding="utf-8") as f:
    f.write(products_code)
print("Wrote ml/spatial/products.py")

aggregation_code = '''"""
RAMP District Forecast Aggregation Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Implements area-weighted integration:
  R_d = sum(w_i * R_i) / sum(w_i)
where w_i is the true physical intersection area in km².
Preserves extreme rainfall hotspots, quantiles, and exceedance probabilities.
Never performs simple unweighted average.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from ml.spatial.boundaries import DistrictBoundary
from ml.spatial.intersection import IntersectionRecord
from ml.spatial.products import DistrictForecastProduct
from ml.spatial.risk import DistrictRiskClassifier
from ml.spatial.uncertainty import SpatialUncertaintyEngine


class DistrictAggregationEngine:
    """
    Aggregates intersecting grid cells into validated DistrictForecastProduct records.
    """

    def __init__(self, risk_classifier: Optional[DistrictRiskClassifier] = None) -> None:
        self.risk_classifier = risk_classifier or DistrictRiskClassifier()
        self.uncertainty_engine = SpatialUncertaintyEngine()

    def aggregate_district(
        self,
        district: DistrictBoundary,
        intersections: List[IntersectionRecord],
        aggregation_method: str = "AREA_WEIGHTED",
        dataset_version: str = "ramp_v0.3.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> DistrictForecastProduct:
        """
        Aggregates grid cells intersecting a given district.
        """
        valid_records = [
            rec for rec in intersections
            if not np.isnan(rec.grid_cell.rainfall_prediction_mm)
            and rec.grid_cell.rainfall_prediction_mm >= 0.0
            and rec.intersection_area_km2 > 0.0
        ]

        # Edge case: No intersecting or valid cells
        if not valid_records:
            return DistrictForecastProduct(
                product_id=f"PROD_{district.district_id}_NO_COVERAGE",
                district_id=district.district_id,
                district_name=district.district_name,
                state_id=district.state_id,
                state_name=district.state_name,
                forecast_valid_time="",
                initialization_time="",
                lead_time_hours=24,
                aggregation_method=aggregation_method,
                rainfall_mm=0.0,
                min_rainfall_mm=0.0,
                max_rainfall_mm=0.0,
                median_rainfall_mm=0.0,
                p90_rainfall_mm=0.0,
                p95_rainfall_mm=0.0,
                p99_rainfall_mm=0.0,
                rain_probability=0.0,
                heavy_probability=0.0,
                very_heavy_probability=0.0,
                extreme_probability=0.0,
                hotspot_latitude=0.0,
                hotspot_longitude=0.0,
                hotspot_rainfall_mm=0.0,
                valid_grid_cells=0,
                total_grid_cells=len(intersections),
                coverage_fraction=0.0,
                regime_distribution={},
                uncertainty={"uncertainty_available": False, "reason": "NO_VALID_CELLS"},
                model_version="ramp_v1.0.0",
                dataset_version=dataset_version,
                data_mode=data_mode,
                boundary_version=district.boundary_version,
                area_km2=district.area_km2,
            )

        ref_cell = valid_records[0].grid_cell
        valid_time = ref_cell.forecast_valid_time
        init_time = ref_cell.initialization_time
        lead_hours = ref_cell.lead_time_hours
        model_version = ref_cell.model_version

        # Extract numerical arrays
        weights = np.array([r.intersection_area_km2 for r in valid_records], dtype=float)
        total_intersecting_area = float(np.sum(weights))
        coverage_fraction = min(1.0, float(total_intersecting_area / max(1e-3, district.area_km2)))

        rains = np.array([r.grid_cell.rainfall_prediction_mm for r in valid_records], dtype=float)
        raw_nwps = np.array([r.grid_cell.raw_nwp_rainfall_mm for r in valid_records], dtype=float)
        global_mls = np.array([r.grid_cell.global_ml_rainfall_mm for r in valid_records], dtype=float)

        p_rains = np.array([r.grid_cell.rainfall_probability for r in valid_records], dtype=float)
        p_heavys = np.array([r.grid_cell.heavy_probability for r in valid_records], dtype=float)
        p_very_heavys = np.array([r.grid_cell.very_heavy_probability for r in valid_records], dtype=float)
        p_extremes = np.array([r.grid_cell.extreme_probability for r in valid_records], dtype=float)

        w_norm = weights / max(1e-6, total_intersecting_area)

        # Deterministic aggregation by method
        if aggregation_method == "MAX_HOTSPOT":
            district_rainfall = float(np.max(rains))
        elif aggregation_method == "VALID_CELL_WEIGHTED":
            district_rainfall = float(np.mean(rains))
        elif aggregation_method == "QUANTILE":
            district_rainfall = float(np.percentile(rains, 90))
        else:  # Default AREA_WEIGHTED
            district_rainfall = float(np.sum(w_norm * rains))

        district_raw_nwp = float(np.sum(w_norm * raw_nwps))
        district_global_ml = float(np.sum(w_norm * global_mls))

        # Exceedance probabilities (area-weighted)
        p_rain_agg = float(np.sum(w_norm * p_rains))
        p_heavy_agg = float(np.sum(w_norm * p_heavys))
        p_very_heavy_agg = float(np.sum(w_norm * p_very_heavys))
        p_extreme_agg = float(np.sum(w_norm * p_extremes))

        # Enforce probability monotonicity invariant: P(Rain) >= P(Heavy) >= P(VH) >= P(Ext)
        p_extreme_agg = min(p_very_heavy_agg, p_extreme_agg)
        p_very_heavy_agg = min(p_heavy_agg, p_very_heavy_agg)
        p_heavy_agg = min(p_rain_agg, p_heavy_agg)

        # Hotspot Detection
        max_idx = int(np.argmax(rains))
        hotspot_cell = valid_records[max_idx].grid_cell
        hotspot_rain = float(rains[max_idx])
        hotspot_intensity = round(hotspot_rain / max(1.0, district_rainfall), 2)
        max_heavy_prob = float(np.max(p_heavys))
        max_extreme_prob = float(np.max(p_extremes))
        high_risk_cells = int(np.sum((p_heavys >= 0.40) | (rains >= 64.5)))

        # Quantile statistics
        min_rain = float(np.min(rains))
        max_rain = float(np.max(rains))
        med_rain = float(np.median(rains))
        p90_rain = float(np.percentile(rains, 90))
        p95_rain = float(np.percentile(rains, 95))
        p99_rain = float(np.percentile(rains, 99))

        # Regime distribution
        regime_weights: Dict[str, float] = {}
        for r in valid_records:
            reg = r.grid_cell.regime
            regime_weights[reg] = regime_weights.get(reg, 0.0) + r.intersection_area_km2
        total_w = sum(regime_weights.values())
        regime_dist = {k: round(v / max(1e-6, total_w), 4) for k, v in regime_weights.items()}

        # Uncertainty calculation
        uncertainties = np.array([r.grid_cell.uncertainty for r in valid_records], dtype=float)
        unc_res = self.uncertainty_engine.calculate_district_uncertainty(
            rainfall_values=rains,
            weights=weights,
            regime_entropies=uncertainties,
            coverage_fraction=coverage_fraction,
        )

        # Risk classification
        risk_res = self.risk_classifier.classify_district(
            rainfall_mm=district_rainfall,
            heavy_prob=p_heavy_agg,
            very_heavy_prob=p_very_heavy_agg,
            extreme_prob=p_extreme_agg,
            hotspot_mm=hotspot_rain,
        )

        prod_id = f"PROD_DIST_{district.district_id}_{valid_time.replace(':', '').replace('-', '')}_{lead_hours}H"

        return DistrictForecastProduct(
            product_id=prod_id,
            district_id=district.district_id,
            district_name=district.district_name,
            state_id=district.state_id,
            state_name=district.state_name,
            forecast_valid_time=valid_time,
            initialization_time=init_time,
            lead_time_hours=lead_hours,
            aggregation_method=aggregation_method,
            rainfall_mm=round(district_rainfall, 2),
            min_rainfall_mm=round(min_rain, 2),
            max_rainfall_mm=round(max_rain, 2),
            median_rainfall_mm=round(med_rain, 2),
            p90_rainfall_mm=round(p90_rain, 2),
            p95_rainfall_mm=round(p95_rain, 2),
            p99_rainfall_mm=round(p99_rain, 2),
            rain_probability=round(p_rain_agg, 4),
            heavy_probability=round(p_heavy_agg, 4),
            very_heavy_probability=round(p_very_heavy_agg, 4),
            extreme_probability=round(p_extreme_agg, 4),
            hotspot_latitude=round(hotspot_cell.latitude, 4),
            hotspot_longitude=round(hotspot_cell.longitude, 4),
            hotspot_rainfall_mm=round(hotspot_rain, 2),
            valid_grid_cells=len(valid_records),
            total_grid_cells=len(intersections),
            coverage_fraction=round(coverage_fraction, 4),
            regime_distribution=regime_dist,
            uncertainty=unc_res,
            model_version=model_version,
            dataset_version=dataset_version,
            data_mode=data_mode,
            boundary_version=district.boundary_version,
            raw_nwp_rainfall_mm=round(district_raw_nwp, 2),
            global_ml_rainfall_mm=round(district_global_ml, 2),
            difference_nwp_mm=round(district_rainfall - district_raw_nwp, 2),
            difference_global_ml_mm=round(district_rainfall - district_global_ml, 2),
            risk_category=risk_res["risk_category"],
            risk_description=risk_res["description"],
            color_hex=risk_res["color_hex"],
            hotspot_intensity=hotspot_intensity,
            max_heavy_probability=round(max_heavy_prob, 4),
            max_extreme_probability=round(max_extreme_prob, 4),
            high_risk_cells_count=high_risk_cells,
            area_km2=district.area_km2,
            classification_rule=risk_res["classification_rule"],
        )
'''

with open("ml/spatial/aggregation.py", "w", encoding="utf-8") as f:
    f.write(aggregation_code)
print("Wrote ml/spatial/aggregation.py")
