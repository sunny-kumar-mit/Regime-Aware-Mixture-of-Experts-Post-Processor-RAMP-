"""
RAMP Authoritative Target Contract
SIH26080 | MoES / NCMRWF

Specifies canonical verification targets:
- Continuous observed rainfall (mm)
- Categorical threshold indicators (0.1, 64.5, 115.6, 204.5 mm)
"""

from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from ml.training.config import (
    RAIN_THRESHOLD_MM,
    HEAVY_THRESHOLD_MM,
    VERY_HEAVY_THRESHOLD_MM,
    EXTREME_THRESHOLD_MM,
    TARGET_SCHEMA_VERSION,
)

TARGET_SPECS = [
    {
        "name": "observed_rainfall_mm",
        "type": "continuous",
        "units": "mm",
        "description": "Daily accumulated rainfall observed by IMD ground truth",
        "min": 0.0,
        "max": 2000.0,
    },
    {
        "name": "rain_label",
        "type": "binary",
        "threshold_mm": RAIN_THRESHOLD_MM,
        "description": "Rain occurrence indicator (>= 0.1 mm/day)",
    },
    {
        "name": "heavy_label",
        "type": "binary",
        "threshold_mm": HEAVY_THRESHOLD_MM,
        "description": "Heavy rainfall alert (>= 64.5 mm/day)",
    },
    {
        "name": "very_heavy_label",
        "type": "binary",
        "threshold_mm": VERY_HEAVY_THRESHOLD_MM,
        "description": "Very heavy rainfall alert (>= 115.6 mm/day)",
    },
    {
        "name": "extreme_label",
        "type": "binary",
        "threshold_mm": EXTREME_THRESHOLD_MM,
        "description": "Extremely heavy rainfall emergency alert (>= 204.5 mm/day)",
    },
]

TARGET_COLUMNS = [t["name"] for t in TARGET_SPECS]


class TargetContractValidator:
    """Validates targets DataFrame against the canonical target schema."""

    @staticmethod
    def validate_targets(df: pd.DataFrame) -> Dict[str, Any]:
        missing = [t for t in TARGET_COLUMNS if t not in df.columns]

        impossible_values = 0
        if "observed_rainfall_mm" in df.columns:
            obs = df["observed_rainfall_mm"].dropna()
            impossible_values = int(((obs < 0.0) | (obs > 2000.0)).sum())

        is_valid = len(missing) == 0 and impossible_values == 0

        return {
            "schema_version": TARGET_SCHEMA_VERSION,
            "target_count": len(TARGET_COLUMNS),
            "is_valid": is_valid,
            "missing_targets": missing,
            "impossible_values_count": impossible_values,
        }

    @staticmethod
    def get_schema_metadata() -> Dict[str, Any]:
        return {
            "schema_version": TARGET_SCHEMA_VERSION,
            "targets": TARGET_SPECS,
        }
