"""
RAMP Phase 7 — Extreme Rainfall Probability Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Converts deterministic RAMP forecasts into calibrated exceedance probabilities:
  P(R > T | RAMP_prediction, regime_context, NWP_features)

for IMD thresholds T ∈ {0.1, 64.5, 115.6, 204.5} mm/24h

Scientific Constraints:
  1. Strict monotonicity: P(R>0.1) ≥ P(R>64.5) ≥ P(R>115.6) ≥ P(R>204.5)
  2. Calibration fitted strictly on VALIDATION split only
  3. Target leakage: zero tolerance
  4. Synthetic honesty: all outputs tagged SYNTHETIC_DEMO
  5. Sample-size guards for extreme events
"""

from ml.extreme_probability.engine import ExtremeRainfallProbabilityEngine
from ml.extreme_probability.schemas import (
    ExtremeProbabilityRecord,
    ExtremeThreshold,
    ProbabilityThresholdResult,
    CalibrationMethod,
    ExtremeModelMetadata,
    ExtremeEngineStatus,
)

__all__ = [
    "ExtremeRainfallProbabilityEngine",
    "ExtremeProbabilityRecord",
    "ExtremeThreshold",
    "ProbabilityThresholdResult",
    "CalibrationMethod",
    "ExtremeModelMetadata",
    "ExtremeEngineStatus",
]
