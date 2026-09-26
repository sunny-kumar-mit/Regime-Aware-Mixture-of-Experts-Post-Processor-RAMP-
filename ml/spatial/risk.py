"""
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
