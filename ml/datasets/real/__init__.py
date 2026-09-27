"""
RAMP Real Paired Dataset Package
SIH26080 | MoES / NCMRWF
Exports RealDatasetPipeline and core data contracts.
"""

from ml.datasets.real.pipeline import (
    RealDatasetPipeline,
    RealPairedRecord,
    RAIN_THRESHOLD_MM,
    HEAVY_THRESHOLD_MM,
    VERY_HEAVY_THRESHOLD_MM,
    EXTREME_THRESHOLD_MM,
    ALLOWED_FEATURE_NAMES,
    FORBIDDEN_FEATURE_NAMES,
)

__all__ = [
    "RealDatasetPipeline",
    "RealPairedRecord",
    "RAIN_THRESHOLD_MM",
    "HEAVY_THRESHOLD_MM",
    "VERY_HEAVY_THRESHOLD_MM",
    "EXTREME_THRESHOLD_MM",
    "ALLOWED_FEATURE_NAMES",
    "FORBIDDEN_FEATURE_NAMES",
]
