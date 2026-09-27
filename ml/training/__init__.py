"""
RAMP Production Model Retraining, Calibration & Registry Package
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF
"""

from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    TARGET_SCHEMA_VERSION,
    ModelLifecycle,
    PROMOTION_GATES,
)
from ml.training.dataset_gate import DatasetGate, RealTrainingEligibilityGate
from ml.training.feature_contract import APPROVED_PREDICTORS, audit_predictor_dataframe
from ml.training.split import TemporalSplitVerifier
from ml.training.baselines import BaselineSuite
from ml.training.global_model import GlobalPrecipitationModel
from ml.training.regime_model import WeatherRegimeModel
from ml.training.moe_model import RAMP_MoE_Model
from ml.training.extreme_models import ExtremeProbabilityModels
from ml.training.calibration import ProbabilityCalibrator
from ml.training.monotonicity import MonotonicityVerifier
from ml.training.registry import ModelRegistry, ModelOverwriteError, GateValidationError
from ml.training.pipeline import TrainingPipeline

__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "TARGET_SCHEMA_VERSION",
    "ModelLifecycle",
    "PROMOTION_GATES",
    "DatasetGate",
    "RealTrainingEligibilityGate",
    "APPROVED_PREDICTORS",
    "audit_predictor_dataframe",
    "TemporalSplitVerifier",
    "BaselineSuite",
    "GlobalPrecipitationModel",
    "WeatherRegimeModel",
    "RAMP_MoE_Model",
    "ExtremeProbabilityModels",
    "ProbabilityCalibrator",
    "MonotonicityVerifier",
    "ModelRegistry",
    "ModelOverwriteError",
    "GateValidationError",
    "TrainingPipeline",
]
