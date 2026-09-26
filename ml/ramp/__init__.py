"""
RAMP: Regime-Aware Mixture-of-Experts Post-Processor
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Core Architecture:
    RAMP(x) = sum_{k=0..6} p_k(x) * Expert_k(x)
where p_k(x) is the calibrated probability of regime k from Phase 4,
and Expert_k(x) is the specialized regression model for regime k.
"""

from ml.ramp.experts import (
    ActiveMonsoonExpert,
    BreakMonsoonExpert,
    CoastalExpert,
    LowDepressionExpert,
    OrographicExpert,
    RegimeExpert,
    TransitionOtherExpert,
    WesternDisturbanceExpert,
)
from ml.ramp.gating import GateWeights, RegimeGatingEngine
from ml.ramp.model import RAMPModel
from ml.ramp.model_registry import RAMPModelMetadata, RAMPModelRegistry
from ml.ramp.inference import RAMPInferenceService, RAMPPredictionRecord
from ml.ramp.training import RAMPTrainer
from ml.ramp.benchmark import RAMPBenchmarkEngine

__all__ = [
    "RegimeExpert",
    "ActiveMonsoonExpert",
    "BreakMonsoonExpert",
    "LowDepressionExpert",
    "CoastalExpert",
    "OrographicExpert",
    "WesternDisturbanceExpert",
    "TransitionOtherExpert",
    "GateWeights",
    "RegimeGatingEngine",
    "RAMPModel",
    "RAMPModelMetadata",
    "RAMPModelRegistry",
    "RAMPInferenceService",
    "RAMPPredictionRecord",
    "RAMPTrainer",
    "RAMPBenchmarkEngine",
]
