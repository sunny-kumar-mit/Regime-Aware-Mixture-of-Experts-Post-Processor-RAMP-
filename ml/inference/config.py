"""
RAMP Operational Forecast Inference Configuration
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Phase 14: Canonical definitions, operational modes, product categories, and schema constants.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Any


FEATURE_SCHEMA_VERSION = "ramp_features_v1.0.0"
TARGET_SCHEMA_VERSION = "ramp_targets_v1.0.0"
INFERENCE_ENGINE_VERSION = "v2.0.0"

# IMD Meteorological Rainfall Thresholds (mm/day)
THRESHOLDS: Dict[str, float] = {
    "rain": 0.1,
    "heavy": 64.5,
    "very_heavy": 115.6,
    "extreme": 204.5,
}

# Operational Product Categories (Part P)
PRODUCT_CATEGORIES = {
    "PRODUCT_1": "Rainfall Forecast (Continuous mm)",
    "PRODUCT_2": "Rainfall Correction (RAMP - Raw NWP)",
    "PRODUCT_3": "Rain Occurrence Probability (>=0.1 mm)",
    "PRODUCT_4": "Heavy Rain Probability (>=64.5 mm)",
    "PRODUCT_5": "Very Heavy Rain Probability (>=115.6 mm)",
    "PRODUCT_6": "Extreme Rain Probability (>=204.5 mm)",
    "PRODUCT_7": "Weather Regime Classification & Soft Gating",
    "PRODUCT_8": "Forecast Uncertainty & Spread",
    "PRODUCT_9": "RAMP vs Raw NWP Difference Field",
}

# Valid Operational Cycles
VALID_CYCLES = ["00 UTC", "06 UTC", "12 UTC", "18 UTC"]

# Standard Grid Coordinates (Phase 8/9/14 canonical)
GRID_LAT_MIN = 6.5
GRID_LAT_MAX = 38.5
GRID_LON_MIN = 66.5
GRID_LON_MAX = 100.5
GRID_RES_DEG = 0.25

# Storage Roots
MODEL_REGISTRY_PATH = Path("ml/model_registry")
FORECAST_STORAGE_PATH = Path("data/processed/forecasts")
AUDIT_LOG_PATH = Path("data/audit/forecasts")
