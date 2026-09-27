"""
RAMP Operational Forecast Inference Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

from ml.inference.config import (
    FEATURE_SCHEMA_VERSION,
    INFERENCE_ENGINE_VERSION,
    PRODUCT_CATEGORIES,
    TARGET_SCHEMA_VERSION,
    THRESHOLDS,
)
from ml.inference.input_resolver import ForecastCycleResolver, ResolvedCycleInfo
from ml.inference.model_resolver import ModelResolver, ResolvedModel
from ml.inference.pipeline import OperationalInferencePipeline
from ml.inference.predictor import RAMPPredictor
from ml.inference.probability import ExtremeProbabilityPredictor
from ml.inference.products import ForecastProductManager
from ml.inference.provenance import ForecastAuditLogger, ForecastManifest, generate_forecast_run_id
from ml.inference.spatial import SpatialForecastEngine
from ml.inference.validation import InputValidationError, InputValidator

__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "INFERENCE_ENGINE_VERSION",
    "PRODUCT_CATEGORIES",
    "TARGET_SCHEMA_VERSION",
    "THRESHOLDS",
    "ForecastCycleResolver",
    "ResolvedCycleInfo",
    "ModelResolver",
    "ResolvedModel",
    "OperationalInferencePipeline",
    "RAMPPredictor",
    "ExtremeProbabilityPredictor",
    "ForecastProductManager",
    "ForecastAuditLogger",
    "ForecastManifest",
    "generate_forecast_run_id",
    "SpatialForecastEngine",
    "InputValidationError",
    "InputValidator",
]
