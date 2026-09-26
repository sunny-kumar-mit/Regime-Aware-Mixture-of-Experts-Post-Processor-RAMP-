"""Append intersection.py, uncertainty.py, risk.py
"""
import os

# 4. ml/spatial/intersection.py
intersection_code = '''"""
RAMP Grid -> District Spatial Intersection Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.strtree import STRtree

from ml.spatial.grid import GridCell
from ml.spatial.boundaries import DistrictBoundary, compute_physical_area_km2


@dataclass
class IntersectionRecord:
    """
    Intersection relationship between a GridCell and a DistrictBoundary.
    """
    grid_id: str
    district_id: str
    state_id: str
    intersection_area_km2: float
    intersection_fraction: float  # Fraction of grid cell that lies inside district
    district_coverage_fraction: float  # Fraction of district area represented by this cell
    grid_cell: GridCell

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "district_id": self.district_id,
            "state_id": self.state_id,
            "intersection_area_km2": round(self.intersection_area_km2, 2),
            "intersection_fraction": round(self.intersection_fraction, 4),
            "district_coverage_fraction": round(self.district_coverage_fraction, 6),
            "rainfall_prediction_mm": self.grid_cell.rainfall_prediction_mm,
            "heavy_probability": self.grid_cell.heavy_probability,
            "very_heavy_probability": self.grid_cell.very_heavy_probability,
            "extreme_probability": self.grid_cell.extreme_probability,
        }


class GridDistrictIntersectionEngine:
    """
    Performs computational geometry intersection between canonical 0.25° grid cells
    and administrative district boundaries using Shapely spatial indexing.
    """

    @classmethod
    def intersect_district_with_cells(
        cls,
        district: DistrictBoundary,
        cells: List[GridCell],
    ) -> List[IntersectionRecord]:
        """
        Intersects a single DistrictBoundary with a collection of GridCells.
        """
        records: List[IntersectionRecord] = []
        dist_geom = district.geometry
        if dist_geom.is_empty:
            return records

        # Filter candidate cells using bounding box check first for efficiency
        min_lon, min_lat, max_lon, max_lat = dist_geom.bounds

        for cell in cells:
            c_bounds = cell.bounds
            # Quick bounding box overlap rejection
            if (
                c_bounds[2] < min_lon
                or c_bounds[0] > max_lon
                or c_bounds[3] < min_lat
                or c_bounds[1] > max_lat
            ):
                continue

            cell_poly = cell.polygon
            if not dist_geom.intersects(cell_poly):
                continue

            try:
                inter_geom = dist_geom.intersection(cell_poly)
                if inter_geom.is_empty or inter_geom.area <= 0.0:
                    continue

                inter_area_km2 = compute_physical_area_km2(inter_geom)
                cell_area_km2 = cell.cell_area_km2
                fraction = min(1.0, max(0.0, inter_area_km2 / max(1e-6, cell_area_km2)))
                dist_frac = inter_area_km2 / max(1e-6, district.area_km2)

                if inter_area_km2 > 0.01:  # reject negligible precision slivers
                    rec = IntersectionRecord(
                        grid_id=cell.grid_id,
                        district_id=district.district_id,
                        state_id=district.state_id,
                        intersection_area_km2=round(inter_area_km2, 2),
                        intersection_fraction=round(fraction, 4),
                        district_coverage_fraction=round(dist_frac, 6),
                        grid_cell=cell,
                    )
                    records.append(rec)
            except Exception:
                continue

        return records

    @classmethod
    def intersect_all_districts(
        cls,
        districts: List[DistrictBoundary],
        cells: List[GridCell],
    ) -> Dict[str, List[IntersectionRecord]]:
        """
        Intersects all districts with grid cells, returning a mapping of district_id -> records.
        """
        results: Dict[str, List[IntersectionRecord]] = {}
        for d in districts:
            recs = cls.intersect_district_with_cells(d, cells)
            results[d.district_id] = recs
        return results
'''

# 5. ml/spatial/uncertainty.py
uncertainty_code = '''"""
RAMP Spatial Uncertainty Propagation Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np


class SpatialUncertaintyEngine:
    """
    Quantifies and propagates grid-level meteorological and regime uncertainty
    to district and state aggregations.
    """

    @staticmethod
    def calculate_district_uncertainty(
        rainfall_values: np.ndarray,
        weights: np.ndarray,
        regime_entropies: Optional[np.ndarray] = None,
        coverage_fraction: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Computes composite uncertainty metrics:
          1. Spatial variance / spread of rainfall across district
          2. Area-weighted standard deviation
          3. Coverage penalty (uncertainty rises when grid coverage is low)
          4. Mean regime entropy (atmospheric state ambiguity)
        """
        if len(rainfall_values) == 0:
            return {
                "uncertainty_available": False,
                "spatial_std_mm": 0.0,
                "coverage_uncertainty": 1.0,
                "composite_uncertainty_score": 1.0,
            }

        w_norm = weights / np.maximum(1e-6, np.sum(weights))
        weighted_mean = float(np.sum(w_norm * rainfall_values))
        weighted_var = float(np.sum(w_norm * (rainfall_values - weighted_mean) ** 2))
        spatial_std = float(np.sqrt(max(0.0, weighted_var)))

        # Coverage uncertainty penalty: 0.0 when 100% coverage, 1.0 when 0%
        cov_penalty = float(np.clip(1.0 - coverage_fraction, 0.0, 1.0))

        # Regime entropy spread
        mean_entropy = float(np.mean(regime_entropies)) if regime_entropies is not None and len(regime_entropies) > 0 else 0.15

        # Composite normalized uncertainty [0, 1]
        norm_spread = float(np.clip(spatial_std / max(1.0, weighted_mean + 10.0), 0.0, 1.0))
        composite = float(np.clip(0.5 * norm_spread + 0.3 * cov_penalty + 0.2 * mean_entropy, 0.0, 1.0))

        return {
            "uncertainty_available": True,
            "weighted_mean_mm": round(weighted_mean, 2),
            "spatial_std_mm": round(spatial_std, 2),
            "coefficient_of_variation": round(spatial_std / max(1e-3, weighted_mean), 3),
            "coverage_fraction": round(coverage_fraction, 4),
            "coverage_penalty": round(cov_penalty, 4),
            "mean_regime_entropy": round(mean_entropy, 4),
            "composite_uncertainty_score": round(composite, 4),
            "uncertainty_tier": "LOW" if composite < 0.25 else ("MEDIUM" if composite < 0.60 else "HIGH"),
        }
'''

# 6. ml/spatial/risk.py
risk_code = '''"""
RAMP District Risk Classification Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Transparent, probability-first rule-based risk classification.
Does NOT claim official IMD warning status. Labeled 'Engineering Risk Classification'.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RiskClassificationRule:
    """
    Defines threshold criteria for risk categorization.
    """
    category: str
    min_rainfall_mm: float
    min_heavy_prob: float
    min_very_heavy_prob: float
    min_extreme_prob: float
    color_hex: str
    description: str


DEFAULT_RISK_RULES: List[RiskClassificationRule] = [
    RiskClassificationRule(
        category="EXTREME_RAINFALL",
        min_rainfall_mm=204.5,
        min_heavy_prob=0.85,
        min_very_heavy_prob=0.60,
        min_extreme_prob=0.40,
        color_hex="#990000",
        description="High probability of extremely heavy rainfall (>=204.5 mm)",
    ),
    RiskClassificationRule(
        category="VERY_HIGH_RAINFALL",
        min_rainfall_mm=115.6,
        min_heavy_prob=0.65,
        min_very_heavy_prob=0.40,
        min_extreme_prob=0.20,
        color_hex="#CC3300",
        description="Substantial probability of very heavy rainfall (>=115.6 mm)",
    ),
    RiskClassificationRule(
        category="HIGH_RAINFALL",
        min_rainfall_mm=64.5,
        min_heavy_prob=0.40,
        min_very_heavy_prob=0.20,
        min_extreme_prob=0.05,
        color_hex="#FF9900",
        description="Moderate to high risk of heavy rainfall (>=64.5 mm)",
    ),
    RiskClassificationRule(
        category="WATCH",
        min_rainfall_mm=15.6,
        min_heavy_prob=0.20,
        min_very_heavy_prob=0.05,
        min_extreme_prob=0.01,
        color_hex="#FFCC00",
        description="Elevated rainfall accumulation or moderate convective risk",
    ),
    RiskClassificationRule(
        category="NORMAL",
        min_rainfall_mm=0.0,
        min_heavy_prob=0.0,
        min_very_heavy_prob=0.0,
        min_extreme_prob=0.0,
        color_hex="#009933",
        description="Normal to moderate monsoon rainfall conditions",
    ),
]


class DistrictRiskClassifier:
    """
    Classifies districts into engineering risk categories based on both
    deterministic rainfall values and calibrated exceedance probabilities.
    """

    def __init__(self, rules: Optional[List[RiskClassificationRule]] = None) -> None:
        self.rules = rules or DEFAULT_RISK_RULES

    def classify_district(
        self,
        rainfall_mm: float,
        heavy_prob: float,
        very_heavy_prob: float,
        extreme_prob: float,
        hotspot_mm: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Classifies district risk using probability-first hierarchy.
        Considers both area-weighted mean and peak hotspot intensity.
        """
        # Iterate from most severe to least severe
        for rule in self.rules:
            # Matches if either deterministic rainfall or probability satisfies thresholds
            matches_rain = (rainfall_mm >= rule.min_rainfall_mm) or (hotspot_mm >= rule.min_rainfall_mm * 1.25)
            matches_prob = (
                (heavy_prob >= rule.min_heavy_prob and rule.min_heavy_prob > 0.0)
                or (very_heavy_prob >= rule.min_very_heavy_prob and rule.min_very_heavy_prob > 0.0)
                or (extreme_prob >= rule.min_extreme_prob and rule.min_extreme_prob > 0.0)
            )

            if rule.category == "NORMAL" or (matches_rain or matches_prob):
                return {
                    "risk_category": rule.category,
                    "color_hex": rule.color_hex,
                    "description": rule.description,
                    "classification_rule": f"Triggered on rain>={rule.min_rainfall_mm}mm OR P(H)>={rule.min_heavy_prob} OR P(VH)>={rule.min_very_heavy_prob} OR P(Ext)>={rule.min_extreme_prob}",
                    "rainfall_value_mm": round(rainfall_mm, 2),
                    "hotspot_value_mm": round(hotspot_mm, 2),
                    "heavy_probability": round(heavy_prob, 4),
                    "very_heavy_probability": round(very_heavy_prob, 4),
                    "extreme_probability": round(extreme_prob, 4),
                    "is_official_warning": False,
                    "disclaimer": "Engineering Risk Classification based on AI post-processing; not an official IMD bulletin.",
                }

        # Fallback
        return {
            "risk_category": "NORMAL",
            "color_hex": "#009933",
            "description": "Normal monsoon conditions",
            "classification_rule": "Fallback default",
            "rainfall_value_mm": round(rainfall_mm, 2),
            "heavy_probability": round(heavy_prob, 4),
            "very_heavy_probability": round(very_heavy_prob, 4),
            "extreme_probability": round(extreme_prob, 4),
            "is_official_warning": False,
            "disclaimer": "Engineering Risk Classification",
        }
'''

with open("ml/spatial/intersection.py", "w", encoding="utf-8") as f:
    f.write(intersection_code)
print("Wrote ml/spatial/intersection.py")

with open("ml/spatial/uncertainty.py", "w", encoding="utf-8") as f:
    f.write(uncertainty_code)
print("Wrote ml/spatial/uncertainty.py")

with open("ml/spatial/risk.py", "w", encoding="utf-8") as f:
    f.write(risk_code)
print("Wrote ml/spatial/risk.py")
