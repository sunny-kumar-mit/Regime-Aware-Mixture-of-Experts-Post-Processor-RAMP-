"""
Phase 7 Extreme Probability Engine — Pydantic Schemas
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Canonical data contracts for the Extreme Rainfall Probability Engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# IMD Threshold Definitions
# =============================================================================

class ExtremeThreshold(str, Enum):
    """
    IMD-standard 24-hour rainfall thresholds.
    Reference: IMD Colour-Coded Rainfall Warnings Criteria
    """
    TRACE    = "0.1"    # Any rainfall occurrence (mm)
    HEAVY    = "64.5"   # Heavy rain (mm)
    VERY_HEAVY = "115.6"  # Very heavy rain (mm)
    EXTREME  = "204.5"  # Extremely heavy rain (mm)

    @property
    def float_value(self) -> float:
        return float(self.value)

    @property
    def label(self) -> str:
        labels = {
            "0.1":   "Rainfall Occurrence (>0.1 mm)",
            "64.5":  "Heavy Rain (>64.5 mm)",
            "115.6": "Very Heavy Rain (>115.6 mm)",
            "204.5": "Extremely Heavy Rain (>204.5 mm)",
        }
        return labels[self.value]

    @property
    def color(self) -> str:
        colors = {
            "0.1":   "#3b82f6",   # blue
            "64.5":  "#f59e0b",   # amber
            "115.6": "#f97316",   # orange
            "204.5": "#dc2626",   # red
        }
        return colors[self.value]

    @property
    def imd_warning(self) -> str:
        warnings = {
            "0.1":   "NONE",
            "64.5":  "YELLOW",
            "115.6": "ORANGE",
            "204.5": "RED",
        }
        return warnings[self.value]


IMD_THRESHOLDS = [
    ExtremeThreshold.TRACE,
    ExtremeThreshold.HEAVY,
    ExtremeThreshold.VERY_HEAVY,
    ExtremeThreshold.EXTREME,
]


# =============================================================================
# Calibration
# =============================================================================

class CalibrationMethod(str, Enum):
    SIGMOID  = "sigmoid"    # Platt scaling
    ISOTONIC = "isotonic"   # Isotonic regression
    NONE     = "none"       # No calibration


# =============================================================================
# Per-Threshold Result
# =============================================================================

class ProbabilityThresholdResult(BaseModel):
    """Calibrated exceedance probability for a single threshold."""
    threshold_mm: float = Field(..., description="IMD threshold in mm/24h")
    threshold_label: str = Field(..., description="Human-readable threshold label")
    imd_warning_color: str = Field(..., description="IMD colour-coded warning level")

    raw_probability: float = Field(
        ..., ge=0.0, le=1.0,
        description="Pre-calibration model output probability"
    )
    calibrated_probability: float = Field(
        ..., ge=0.0, le=1.0,
        description="Post-calibration probability after Platt/Isotonic scaling"
    )
    calibration_method: str = Field("none", description="Calibration method applied")

    # Uncertainty band
    probability_lower: float = Field(0.0, ge=0.0, le=1.0, description="5th percentile bootstrap CI")
    probability_upper: float = Field(1.0, ge=0.0, le=1.0, description="95th percentile bootstrap CI")

    # Top feature importance for this threshold (name → gain)
    top_features: Dict[str, float] = Field(default_factory=dict)

    # Training statistics
    train_event_rate: float = Field(0.0, description="Base rate of exceedance in training set")
    train_n_events: int = Field(0, description="Training positive event count")
    train_n_total: int = Field(0, description="Training sample count")
    sample_size_warning: bool = Field(False, description="True when extreme events < 50 in training")


# =============================================================================
# Unified Prediction Record
# =============================================================================

class ExtremeProbabilityRecord(BaseModel):
    """
    Complete Phase 7 extreme exceedance probability prediction.
    Maintains strict monotonicity invariant after reconciliation.
    """
    sample_id: str
    forecast_valid_time: str
    latitude: float
    longitude: float
    lead_time_hours: int

    # RAMP deterministic context (frozen ramp_v1.0.0)
    ramp_prediction_mm: float = Field(..., description="Deterministic RAMP rainfall forecast (mm)")
    raw_nwp_prediction_mm: float = Field(..., description="Raw NWP forecast (mm)")
    top_regime: str
    regime_confidence: float

    # Per-threshold calibrated probabilities (monotonicity guaranteed)
    p_trace: float = Field(..., ge=0.0, le=1.0, description="P(R > 0.1 mm) — rainfall occurrence")
    p_heavy: float = Field(..., ge=0.0, le=1.0, description="P(R > 64.5 mm) — heavy rain")
    p_very_heavy: float = Field(..., ge=0.0, le=1.0, description="P(R > 115.6 mm) — very heavy rain")
    p_extreme: float = Field(..., ge=0.0, le=1.0, description="P(R > 204.5 mm) — extremely heavy rain")

    # Detailed results per threshold
    threshold_results: List[ProbabilityThresholdResult] = Field(default_factory=list)

    # Monotonicity audit
    monotonicity_satisfied: bool = Field(True, description="Whether p_trace >= p_heavy >= p_very_heavy >= p_extreme")
    monotonicity_corrections_applied: int = Field(0, description="Number of isotonic reconciliation corrections")

    # Composite risk index [0, 1]
    composite_risk_index: float = Field(0.0, ge=0.0, le=1.0)
    risk_category: str = Field("LOW", description="LOW / MODERATE / HIGH / SEVERE / EXTREME")
    imd_warning_recommendation: str = Field("NONE", description="Recommended IMD colour-coded warning")

    # Metadata
    model_version: str = Field("extreme_v1.0.0")
    data_mode: str = Field("SYNTHETIC_DEMO")
    computed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# =============================================================================
# Model Metadata
# =============================================================================

class ExtremeModelMetadata(BaseModel):
    """Metadata for a single threshold binary classifier."""
    threshold_mm: float
    threshold_label: str
    model_type: str = "LightGBM"
    version: str = "extreme_v1.0.0"
    calibration_method: str = "sigmoid"
    is_fitted: bool = False
    train_n_samples: int = 0
    train_n_events: int = 0
    train_event_rate: float = 0.0
    val_brier_score: float = 0.0
    val_roc_auc: float = 0.0
    val_pr_auc: float = 0.0
    val_ece: float = 0.0
    sample_size_warning: bool = False
    feature_count: int = 0
    feature_names: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ExtremeEngineStatus(BaseModel):
    """Status summary for the complete extreme probability engine."""
    engine_version: str = "extreme_v1.0.0"
    ramp_source_version: str = "ramp_v1.0.0"
    data_mode: str = "SYNTHETIC_DEMO"
    n_thresholds: int = 4
    thresholds: List[float] = Field(default_factory=lambda: [0.1, 64.5, 115.6, 204.5])
    models_status: Dict[str, bool] = Field(default_factory=dict)
    all_fitted: bool = False
    monotonicity_enforced: bool = True
    calibration_applied: bool = True
    last_trained_at: Optional[str] = None
    operational: bool = False
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# Evaluation Metrics
# =============================================================================

class BrierSkillScore(BaseModel):
    """Brier Skill Score relative to climatological reference forecast."""
    threshold_mm: float
    brier_score: float
    brier_reference: float
    brier_skill_score: float
    interpretation: str


class CalibrationDiagnostic(BaseModel):
    """Reliability diagram bin data for ECE computation."""
    threshold_mm: float
    n_bins: int = 10
    bin_confidence: List[float] = Field(default_factory=list)
    bin_accuracy: List[float] = Field(default_factory=list)
    bin_counts: List[int] = Field(default_factory=list)
    expected_calibration_error: float = 0.0
    max_calibration_error: float = 0.0


class PRCurveData(BaseModel):
    """Precision-Recall curve data for a threshold."""
    threshold_mm: float
    precision: List[float] = Field(default_factory=list)
    recall: List[float] = Field(default_factory=list)
    pr_auc: float = 0.0
    average_precision: float = 0.0
    baseline_precision: float = 0.0  # = event rate


class ExtremeEvaluationSuite(BaseModel):
    """Complete evaluation results for all thresholds."""
    data_mode: str = "SYNTHETIC_DEMO"
    n_test_samples: int = 0
    brier_scores: List[BrierSkillScore] = Field(default_factory=list)
    calibration_diagnostics: List[CalibrationDiagnostic] = Field(default_factory=list)
    pr_curves: List[PRCurveData] = Field(default_factory=list)
    roc_auc_per_threshold: Dict[str, float] = Field(default_factory=dict)
    monotonicity_violation_rate: float = 0.0
    evaluated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
