"""
RAMP Model Training Configuration & Constants
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Any


# Canonical Schema Versions
FEATURE_SCHEMA_VERSION = "ramp_features_v1.0.0"
TARGET_SCHEMA_VERSION = "ramp_targets_v1.0.0"
DATASET_VERSION = "ramp_dataset_real_v1.0.0"
TRAINING_PIPELINE_VERSION = "v2.0.0"

# Target Rainfall Thresholds (IMD Classification, mm/day)
RAIN_THRESHOLD_MM = 0.1
HEAVY_THRESHOLD_MM = 64.5
VERY_HEAVY_THRESHOLD_MM = 115.6
EXTREME_THRESHOLD_MM = 204.5

THRESHOLDS: Dict[str, float] = {
    "rain": RAIN_THRESHOLD_MM,
    "heavy": HEAVY_THRESHOLD_MM,
    "very_heavy": VERY_HEAVY_THRESHOLD_MM,
    "extreme": EXTREME_THRESHOLD_MM,
}

# Model Lifecycle States (Section Part W)
class ModelLifecycle(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATED = "VALIDATED"
    CANDIDATE = "CANDIDATE"
    PRODUCTION_READY = "PRODUCTION_READY"
    ARCHIVED = "ARCHIVED"
    BLOCKED = "BLOCKED"


# 12 Mandatory Model Promotion Gates (Section Part X)
MANDATORY_PROMOTION_GATES = [
    "DATASET_VALID",
    "LEAKAGE_FREE",
    "FEATURE_SCHEMA_VALID",
    "TARGET_SCHEMA_VALID",
    "TEMPORAL_SPLIT_VALID",
    "TRAINING_COMPLETED",
    "VALIDATION_COMPLETED",
    "TEST_EVALUATION_COMPLETED",
    "CALIBRATION_COMPLETED",
    "MONOTONICITY_VALID",
    "PROVENANCE_COMPLETE",
    "CHECKSUM_VALID",
]
PROMOTION_GATES = MANDATORY_PROMOTION_GATES


# Canonical Model Identifiers for Phase 13
MODEL_REGISTRY_IDS = {
    "global": "ramp_global_v2.0.0",
    "regime": "ramp_regime_v2.0.0",
    "moe": "ramp_moe_v2.0.0",
    "extreme": "ramp_extreme_v2.0.0",
}

# Default Paths
PROJECT_ROOT = Path("d:/SIH26080")
DATASET_DIR = PROJECT_ROOT / "ml" / "datasets" / "real" / DATASET_VERSION
MODEL_REGISTRY_DIR = PROJECT_ROOT / "ml" / "model_registry"
