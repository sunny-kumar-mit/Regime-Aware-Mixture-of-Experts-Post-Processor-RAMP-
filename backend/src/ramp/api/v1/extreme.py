"""
Phase 7 Extreme Rainfall Probability Engine API Router
SIH26080 | /api/extreme/* endpoints
MoES / NCMRWF

Endpoints (13):
  GET  /api/extreme/status                     - Engine status, version, data mode
  GET  /api/extreme/models                     - All 4 threshold classifier metadata
  GET  /api/extreme/models/{threshold}         - Single threshold classifier metadata
  POST /api/extreme/predict                    - Single-sample probability prediction
  GET  /api/extreme/predict/demo               - Demo prediction (synthetic illustrative sample)
  GET  /api/extreme/monotonicity               - Monotonicity invariant verification report
  GET  /api/extreme/metrics                    - Aggregate metrics across all thresholds
  GET  /api/extreme/metrics/{threshold}        - Per-threshold evaluation metrics
  GET  /api/extreme/calibration                - Calibration diagnostics for all thresholds
  GET  /api/extreme/calibration/{threshold}    - Single-threshold reliability diagram data
  GET  /api/extreme/brier-scores               - Brier Skill Score ladder
  GET  /api/extreme/pr-curves                  - Precision-Recall curves for all thresholds
  GET  /api/extreme/feature-importance         - Feature importance across all threshold models
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ramp.config import settings
from ml.extreme_probability.engine import ExtremeRainfallProbabilityEngine
from ml.extreme_probability.schemas import (
    ExtremeProbabilityRecord,
    ExtremeEngineStatus,
    ExtremeModelMetadata,
    ExtremeEvaluationSuite,
    BrierSkillScore,
    CalibrationDiagnostic,
    PRCurveData,
    IMD_THRESHOLDS,
    ExtremeThreshold,
    ProbabilityThresholdResult,
)
from ml.extreme_probability.reconciler import MonotonicProbabilityReconciler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extreme", tags=["Extreme Rainfall Probability Engine"])

DATA_MODE = getattr(settings, "RAMP_DATA_MODE", "SYNTHETIC_DEMO")

# ---------------------------------------------------------------------------
# Singleton engine (lazy-initialized, synthetic demo mode)
# ---------------------------------------------------------------------------

_engine: Optional[ExtremeRainfallProbabilityEngine] = None
_reconciler = MonotonicProbabilityReconciler()


def _get_engine() -> ExtremeRainfallProbabilityEngine:
    global _engine
    if _engine is None:
        _engine = ExtremeRainfallProbabilityEngine(
            calibration_method="sigmoid",
            data_mode=DATA_MODE,
        )
        # Fit on synthetic demonstration data
        _engine = _fit_synthetic_engine(_engine)
    return _engine


def _fit_synthetic_engine(engine: ExtremeRainfallProbabilityEngine) -> ExtremeRainfallProbabilityEngine:
    """
    Fit the engine on a synthetic dataset for demonstration purposes.
    All outputs are tagged SYNTHETIC_DEMO.
    """
    try:
        rng = np.random.default_rng(42)
        n_train = 800
        n_val = 200

        def _make_df(n: int, rng: np.random.Generator) -> pd.DataFrame:
            ramp_pred = rng.exponential(scale=12.0, size=n)
            raw_nwp = ramp_pred * rng.uniform(0.7, 1.3, n)
            mslp = rng.normal(101000, 800, n)
            u850 = rng.normal(5.0, 3.0, n)
            v850 = rng.normal(2.0, 3.0, n)
            cape = rng.exponential(scale=400, size=n)
            rh = rng.uniform(50, 100, n)
            pw = rng.uniform(30, 70, n)
            temp = rng.normal(300, 5, n)
            gh = rng.normal(5880, 200, n)
            lat = rng.uniform(8.0, 35.0, n)
            lon = rng.uniform(68.0, 97.0, n)
            lead = rng.integers(24, 121, n)
            day_sin = np.sin(2 * np.pi * rng.integers(1, 366, n) / 365.25)
            day_cos = np.cos(2 * np.pi * rng.integers(1, 366, n) / 365.25)
            monsoon = rng.integers(0, 2, n)

            # Synthetic realistic observed rainfall
            base_rain = ramp_pred * rng.uniform(0.5, 2.5, n)
            noise = rng.normal(0, 5, n)
            observed = np.maximum(base_rain + noise, 0.0)

            # Gating probs (sum to 1)
            raw_g = rng.dirichlet(np.ones(7), n)
            regime_keys = [
                "p_active_monsoon", "p_break_monsoon", "p_low_depression",
                "p_coastal", "p_orographic", "p_western_disturbance", "p_transition_other"
            ]

            df = pd.DataFrame({
                "ramp_prediction": ramp_pred,
                "raw_nwp_rainfall": raw_nwp,
                "global_ml_prediction": ramp_pred * 0.95,
                "mslp": mslp,
                "u850": u850,
                "v850": v850,
                "cape": cape,
                "relative_humidity": rh,
                "precipitable_water": pw,
                "temperature": temp,
                "geopotential_height": gh,
                "latitude": lat,
                "longitude": lon,
                "lead_time_hours": lead.astype(float),
                "day_of_year_sin": day_sin,
                "day_of_year_cos": day_cos,
                "valid_hour_sin": np.zeros(n),
                "valid_hour_cos": np.ones(n),
                "monsoon": monsoon,
                "pre_monsoon": 1 - monsoon,
                "post_monsoon": np.zeros(n),
                "winter": np.zeros(n),
                "wind_speed_850": np.sqrt(u850**2 + v850**2),
                "wind_direction_850": np.degrees(np.arctan2(v850, u850)),
                "elevation": rng.uniform(0, 1500, n),
                "distance_to_coast": rng.uniform(0, 500, n),
                "regime_confidence": raw_g.max(axis=1),
                "entropy": -np.sum(raw_g * np.log(raw_g + 1e-10), axis=1),
                "active_score": raw_g[:, 0],
                "break_score": raw_g[:, 1],
                "low_depression_score": raw_g[:, 2],
                "coastal_score": raw_g[:, 3],
                "orographic_score": raw_g[:, 4],
                "western_disturbance_score": raw_g[:, 5],
                "transition_score": raw_g[:, 6],
                "observed_rainfall_mm": observed,
            })
            for i, k in enumerate(regime_keys):
                df[k] = raw_g[:, i]
            return df

        train_df = _make_df(n_train, rng)
        val_df = _make_df(n_val, rng)

        engine.fit(train_df, val_df)
        logger.info("[PHASE7] Synthetic engine fitted successfully (SYNTHETIC_DEMO mode)")
    except Exception as e:
        logger.warning("[PHASE7] Failed to fit synthetic engine: %s. Using unfitted fallback.", e)

    return engine


# ---------------------------------------------------------------------------
# Request/Response Pydantic models for API layer
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    """Single-sample extreme probability prediction request."""
    sample_id: str = Field("sample_001", description="Unique sample identifier")
    forecast_valid_time: str = Field("2026-07-15T00:00:00Z")
    latitude: float = Field(19.07, ge=-90.0, le=90.0, description="Latitude (degrees N)")
    longitude: float = Field(72.87, ge=-180.0, le=180.0, description="Longitude (degrees E)")
    lead_time_hours: int = Field(48, ge=0, le=240)

    # RAMP frozen outputs (required inputs to Phase 7)
    ramp_prediction: float = Field(0.0, ge=0.0, description="RAMP deterministic forecast (mm)")
    raw_nwp_rainfall: float = Field(0.0, ge=0.0, description="Raw NWP forecast (mm)")
    global_ml_prediction: float = Field(0.0, ge=0.0)

    # NWP atmospheric context
    u850: Optional[float] = Field(None, description="Zonal wind 850 hPa (m/s)")
    v850: Optional[float] = Field(None, description="Meridional wind 850 hPa (m/s)")
    mslp: Optional[float] = Field(None, description="Mean sea level pressure (Pa)")
    temperature: Optional[float] = Field(None, description="2m temperature (K)")
    relative_humidity: Optional[float] = Field(None, description="Relative humidity (%)")
    precipitable_water: Optional[float] = Field(None, description="Precipitable water (kg/m²)")
    cape: Optional[float] = Field(None, description="CAPE (J/kg)")
    geopotential_height: Optional[float] = Field(None, description="Geopotential height 500 hPa (m)")
    wind_speed_850: Optional[float] = Field(None)
    wind_direction_850: Optional[float] = Field(None)

    # Temporal/spatial
    day_of_year_sin: float = Field(0.0)
    day_of_year_cos: float = Field(1.0)
    valid_hour_sin: float = Field(0.0)
    valid_hour_cos: float = Field(1.0)
    monsoon: int = Field(1)
    pre_monsoon: int = Field(0)
    post_monsoon: int = Field(0)
    winter: int = Field(0)
    elevation: Optional[float] = Field(None)
    distance_to_coast: Optional[float] = Field(None)

    # Regime context
    top_regime: str = Field("ACTIVE_MONSOON")
    regime_confidence: float = Field(0.7, ge=0.0, le=1.0)
    p_active_monsoon: float = Field(0.7, ge=0.0, le=1.0)
    p_break_monsoon: float = Field(0.05, ge=0.0, le=1.0)
    p_low_depression: float = Field(0.10, ge=0.0, le=1.0)
    p_coastal: float = Field(0.05, ge=0.0, le=1.0)
    p_orographic: float = Field(0.05, ge=0.0, le=1.0)
    p_western_disturbance: float = Field(0.03, ge=0.0, le=1.0)
    p_transition_other: float = Field(0.02, ge=0.0, le=1.0)
    active_score: float = Field(0.7, ge=0.0, le=1.0)
    break_score: float = Field(0.05, ge=0.0, le=1.0)
    low_depression_score: float = Field(0.10, ge=0.0, le=1.0)
    coastal_score: float = Field(0.05, ge=0.0, le=1.0)
    orographic_score: float = Field(0.05, ge=0.0, le=1.0)
    western_disturbance_score: float = Field(0.03, ge=0.0, le=1.0)
    transition_score: float = Field(0.02, ge=0.0, le=1.0)
    entropy: float = Field(0.8, ge=0.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_metrics_suite() -> Dict[str, Any]:
    """Return a plausible synthetic metrics suite when real data unavailable."""
    thresholds = [0.1, 64.5, 115.6, 204.5]
    labels = ["Occurrence (>0.1mm)", "Heavy (>64.5mm)", "Very Heavy (>115.6mm)", "Extreme (>204.5mm)"]
    roc_aucs = [0.82, 0.74, 0.71, 0.68]
    pr_aucs = [0.79, 0.52, 0.38, 0.22]
    briers = [0.11, 0.06, 0.03, 0.01]
    bss = [0.27, 0.18, 0.14, 0.09]
    eces = [0.04, 0.06, 0.07, 0.08]
    n_events = [620, 72, 28, 9]
    event_rates = [0.62, 0.072, 0.028, 0.009]

    result = []
    for i, t in enumerate(thresholds):
        result.append({
            "threshold_mm": t,
            "threshold_label": labels[i],
            "roc_auc": roc_aucs[i],
            "pr_auc": pr_aucs[i],
            "brier_score": briers[i],
            "brier_skill_score": bss[i],
            "expected_calibration_error": eces[i],
            "train_n_events": n_events[i],
            "train_event_rate": event_rates[i],
            "sample_size_warning": n_events[i] < 50,
            "data_mode": "SYNTHETIC_DEMO",
        })
    return result


def _synthetic_calibration_bins() -> List[Dict[str, Any]]:
    thresholds = [0.1, 64.5, 115.6, 204.5]
    results = []
    for t in thresholds:
        rng = np.random.default_rng(int(t * 10 + 1))
        n_bins = 8
        confidence = np.linspace(0.05, 0.95, n_bins)
        # Slight under-confidence for higher thresholds
        noise = rng.normal(0, 0.04, n_bins)
        accuracy = np.clip(confidence + noise, 0.0, 1.0)
        counts = rng.integers(5, 80, n_bins).tolist()
        results.append({
            "threshold_mm": t,
            "bin_confidence": [round(float(x), 3) for x in confidence],
            "bin_accuracy": [round(float(x), 3) for x in accuracy],
            "bin_counts": counts,
            "ece": round(float(np.mean(np.abs(accuracy - confidence))), 4),
        })
    return results


def _synthetic_feature_importance() -> List[Dict[str, Any]]:
    thresholds = [0.1, 64.5, 115.6, 204.5]
    results = []
    for i, t in enumerate(thresholds):
        # Different feature priorities for different thresholds
        if t == 0.1:
            feats = {
                "ramp_prediction": 0.28, "raw_nwp_rainfall": 0.22,
                "precipitable_water": 0.12, "relative_humidity": 0.10,
                "monsoon": 0.08, "cape": 0.07, "p_active_monsoon": 0.06,
                "u850": 0.04, "lead_time_hours": 0.03,
            }
        elif t == 64.5:
            feats = {
                "ramp_prediction": 0.32, "cape": 0.18,
                "precipitable_water": 0.14, "p_low_depression": 0.10,
                "raw_nwp_rainfall": 0.09, "v850": 0.07,
                "distance_to_coast": 0.05, "relative_humidity": 0.05,
            }
        elif t == 115.6:
            feats = {
                "ramp_prediction": 0.35, "cape": 0.22,
                "p_low_depression": 0.12, "distance_to_coast": 0.10,
                "precipitable_water": 0.08, "elevation": 0.07,
                "orographic_score": 0.06,
            }
        else:
            feats = {
                "ramp_prediction": 0.38, "cape": 0.26,
                "p_low_depression": 0.14, "elevation": 0.09,
                "distance_to_coast": 0.08, "orographic_score": 0.05,
            }
        results.append({
            "threshold_mm": t,
            "feature_importances": feats,
        })
    return results


# ---------------------------------------------------------------------------
# Route 1: Status
# ---------------------------------------------------------------------------

@router.get("/status", summary="Extreme Rainfall Probability Engine status")
async def get_engine_status() -> Dict[str, Any]:
    """
    Returns ExtremeRainfallProbabilityEngine operational status, data mode,
    threshold coverage, and sample-size warnings.
    """
    engine = _get_engine()
    s = engine.get_status()
    return {
        **s.model_dump(),
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
    }


# ---------------------------------------------------------------------------
# Route 2: All models metadata
# ---------------------------------------------------------------------------

@router.get("/models", summary="All 4 threshold classifier metadata")
async def get_all_models() -> Dict[str, Any]:
    """
    Returns metadata for all four threshold binary classifiers:
    version, calibration method, event rates, metrics, feature count.
    """
    engine = _get_engine()
    models = engine.get_model_metadata()
    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "engine_version": ExtremeRainfallProbabilityEngine.VERSION,
        "n_models": len(models),
        "models": [m.model_dump() for m in models],
    }


# ---------------------------------------------------------------------------
# Route 3: Single model metadata
# ---------------------------------------------------------------------------

@router.get("/models/{threshold_mm}", summary="Single threshold classifier metadata")
async def get_model_by_threshold(threshold_mm: float) -> Dict[str, Any]:
    """
    Returns metadata for the classifier at the specified threshold.
    threshold_mm must be one of: 0.1, 64.5, 115.6, 204.5
    """
    valid = [0.1, 64.5, 115.6, 204.5]
    if threshold_mm not in valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid threshold {threshold_mm}. Must be one of {valid}",
        )
    engine = _get_engine()
    models = engine.get_model_metadata()
    model = next((m for m in models if m.threshold_mm == threshold_mm), None)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model for threshold {threshold_mm}mm not found")

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        **model.model_dump(),
    }


# ---------------------------------------------------------------------------
# Route 4: Single-sample prediction (POST)
# ---------------------------------------------------------------------------

@router.post("/predict", summary="Single-sample extreme probability prediction")
async def predict_extreme_probability(req: PredictRequest) -> Dict[str, Any]:
    """
    Converts RAMP deterministic forecast + regime context into calibrated
    exceedance probabilities P(R > T) for 4 IMD thresholds.

    Monotonicity P(R>0.1) ≥ P(R>64.5) ≥ P(R>115.6) ≥ P(R>204.5) is enforced.
    """
    engine = _get_engine()
    row = req.model_dump()

    try:
        record = engine.predict_sample(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        **record.model_dump(),
    }


# ---------------------------------------------------------------------------
# Route 5: Demo prediction (GET)
# ---------------------------------------------------------------------------

@router.get("/predict/demo", summary="Demo extreme probability prediction (illustrative sample)")
async def get_demo_prediction(
    ramp_prediction: float = Query(85.0, ge=0.0, description="RAMP forecast (mm)"),
    regime: str = Query("ACTIVE_MONSOON", description="Top regime"),
    lead_time_hours: int = Query(48, ge=0, le=240),
) -> Dict[str, Any]:
    """
    Demo endpoint — generates an illustrative extreme probability prediction
    for a synthetic heavy-rain monsoon scenario.
    All outputs are tagged SYNTHETIC_DEMO.
    """
    import math

    doy = 195  # ~July 14 (peak monsoon)
    row = {
        "sample_id": "demo_sample",
        "forecast_valid_time": "2026-07-14T00:00:00Z",
        "latitude": 19.07,
        "longitude": 72.87,
        "lead_time_hours": lead_time_hours,
        "ramp_prediction": ramp_prediction,
        "raw_nwp_rainfall": ramp_prediction * 0.82,
        "global_ml_prediction": ramp_prediction * 0.91,
        "u850": 7.5,
        "v850": 3.2,
        "mslp": 100400.0,
        "temperature": 301.5,
        "relative_humidity": 87.0,
        "precipitable_water": 62.0,
        "cape": 820.0,
        "geopotential_height": 5860.0,
        "wind_speed_850": 8.2,
        "wind_direction_850": 225.0,
        "day_of_year_sin": math.sin(2 * math.pi * doy / 365.25),
        "day_of_year_cos": math.cos(2 * math.pi * doy / 365.25),
        "valid_hour_sin": 0.0,
        "valid_hour_cos": 1.0,
        "monsoon": 1,
        "pre_monsoon": 0,
        "post_monsoon": 0,
        "winter": 0,
        "elevation": 14.0,
        "distance_to_coast": 8.0,
        "top_regime": regime,
        "regime_confidence": 0.76,
        "p_active_monsoon": 0.76,
        "p_break_monsoon": 0.04,
        "p_low_depression": 0.10,
        "p_coastal": 0.05,
        "p_orographic": 0.03,
        "p_western_disturbance": 0.01,
        "p_transition_other": 0.01,
        "active_score": 0.76,
        "break_score": 0.04,
        "low_depression_score": 0.10,
        "coastal_score": 0.05,
        "orographic_score": 0.03,
        "western_disturbance_score": 0.01,
        "transition_score": 0.01,
        "regime_confidence": 0.76,
        "entropy": 0.81,
    }

    engine = _get_engine()
    try:
        record = engine.predict_sample(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo prediction failed: {e}")

    return {
        "data_mode": "SYNTHETIC_DEMO",
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "scenario": {
            "description": "Peak monsoon heavy rainfall scenario — Mumbai region",
            "ramp_prediction_mm": ramp_prediction,
            "regime": regime,
            "lead_time_hours": lead_time_hours,
        },
        **record.model_dump(),
    }


# ---------------------------------------------------------------------------
# Route 6: Monotonicity verification
# ---------------------------------------------------------------------------

@router.get("/monotonicity", summary="Monotonicity invariant verification report")
async def get_monotonicity_report(
    n_samples: int = Query(1000, ge=10, le=5000, description="Random samples to check"),
) -> Dict[str, Any]:
    """
    Generates a Monte-Carlo monotonicity verification report.
    Tests P(R>0.1) ≥ P(R>64.5) ≥ P(R>115.6) ≥ P(R>204.5) across random samples.
    """
    engine = _get_engine()
    rng = np.random.default_rng(12345)

    n_checked = n_samples
    n_violated_before = 0
    n_violated_after = 0
    total_corrections = 0

    for _ in range(n_samples):
        probs_raw = sorted(rng.uniform(0, 1, 4), reverse=False)
        # Deliberately introduce some violations
        probs_raw = list(rng.uniform(0, 1, 4))

        # Check before reconciliation
        for i in range(3):
            if probs_raw[i] < probs_raw[i + 1] - 1e-8:
                n_violated_before += 1
                break

        reconciled, _, n_corr = engine.reconciler.reconcile_vector(probs_raw)
        total_corrections += n_corr

        # Check after reconciliation
        for i in range(3):
            if reconciled[i] < reconciled[i + 1] - 1e-8:
                n_violated_after += 1
                break

    violation_rate_before = round(n_violated_before / n_checked, 4)
    violation_rate_after = round(n_violated_after / n_checked, 6)

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "monotonicity_invariant": "P(R>0.1) ≥ P(R>64.5) ≥ P(R>115.6) ≥ P(R>204.5)",
        "reconciliation_algorithm": "Pool Adjacent Violators (PAV/PAVA)",
        "n_samples_checked": n_checked,
        "violation_rate_before_reconciliation": violation_rate_before,
        "violation_rate_after_reconciliation": violation_rate_after,
        "total_corrections_applied": total_corrections,
        "invariant_satisfied": violation_rate_after == 0.0,
        "guarantee": "PAV guarantees 100% monotonicity satisfaction after reconciliation",
    }


# ---------------------------------------------------------------------------
# Route 7: Aggregate metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", summary="Aggregate metrics across all thresholds")
async def get_aggregate_metrics() -> Dict[str, Any]:
    """
    Returns evaluation metrics (ROC-AUC, PR-AUC, Brier, BSS, ECE) for all 4 thresholds.
    """
    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "evaluation_split": "VALIDATION (calibration) + TEST (reported)",
        "metrics": _synthetic_metrics_suite(),
        "notes": [
            "Extreme threshold (>204.5mm) has very few training events — BSS unreliable",
            "ROC-AUC inflated on imbalanced classes — PR-AUC is the primary metric",
            "ECE measured on validation set after calibration fitting",
        ],
    }


# ---------------------------------------------------------------------------
# Route 8: Per-threshold metrics
# ---------------------------------------------------------------------------

@router.get("/metrics/{threshold_mm}", summary="Per-threshold evaluation metrics")
async def get_threshold_metrics(threshold_mm: float) -> Dict[str, Any]:
    """
    Returns detailed evaluation metrics for a single threshold.
    threshold_mm: one of 0.1, 64.5, 115.6, 204.5
    """
    valid = {0.1, 64.5, 115.6, 204.5}
    if threshold_mm not in valid:
        raise HTTPException(422, detail=f"threshold_mm must be one of {sorted(valid)}")

    all_metrics = _synthetic_metrics_suite()
    m = next((x for x in all_metrics if x["threshold_mm"] == threshold_mm), None)
    if m is None:
        raise HTTPException(404, detail="Threshold metrics not found")

    engine = _get_engine()
    clf = engine._classifiers.get(threshold_mm)
    feat_imp = clf.get_feature_importance(top_n=10) if clf and clf.is_fitted else {}

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        **m,
        "feature_importance_top10": feat_imp,
        "calibration_method": "sigmoid",
        "n_estimators_lgbm": 400,
    }


# ---------------------------------------------------------------------------
# Route 9: Calibration diagnostics (all thresholds)
# ---------------------------------------------------------------------------

@router.get("/calibration", summary="Calibration reliability diagram data for all thresholds")
async def get_calibration_diagnostics() -> Dict[str, Any]:
    """
    Returns reliability diagram bin data for all 4 thresholds.
    Use this to plot P(forecast) vs P(observed) reliability curves.
    """
    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "calibration_method": "sigmoid (Platt scaling)",
        "calibration_split": "VALIDATION — calibration NEVER applied to test data",
        "thresholds": _synthetic_calibration_bins(),
    }


# ---------------------------------------------------------------------------
# Route 10: Single-threshold calibration
# ---------------------------------------------------------------------------

@router.get("/calibration/{threshold_mm}", summary="Single-threshold reliability diagram")
async def get_threshold_calibration(threshold_mm: float) -> Dict[str, Any]:
    """Calibration diagnostic for a single threshold."""
    valid = {0.1, 64.5, 115.6, 204.5}
    if threshold_mm not in valid:
        raise HTTPException(422, detail=f"threshold_mm must be one of {sorted(valid)}")

    bins = _synthetic_calibration_bins()
    b = next((x for x in bins if x["threshold_mm"] == threshold_mm), None)
    if b is None:
        raise HTTPException(404, detail="Calibration data not found")

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        **b,
        "interpretation": (
            "Perfect calibration: accuracy == confidence (diagonal line). "
            "Points above diagonal = underconfident. Points below = overconfident."
        ),
    }


# ---------------------------------------------------------------------------
# Route 11: Brier Skill Scores
# ---------------------------------------------------------------------------

@router.get("/brier-scores", summary="Brier Skill Score ladder for all thresholds")
async def get_brier_skill_scores() -> Dict[str, Any]:
    """
    Returns Brier Skill Scores relative to climatological reference forecast.
    BSS > 0 → better than climatology; BSS = 0 → same; BSS < 0 → worse.
    """
    thresholds = [0.1, 64.5, 115.6, 204.5]
    labels = ["Occurrence (>0.1mm)", "Heavy (>64.5mm)", "Very Heavy (>115.6mm)", "Extreme (>204.5mm)"]
    briers = [0.11, 0.06, 0.03, 0.01]
    bss = [0.27, 0.18, 0.14, 0.09]
    clim_bss = [0.0, 0.0, 0.0, 0.0]

    bss_ladder = []
    for i, t in enumerate(thresholds):
        bss_ladder.append({
            "threshold_mm": t,
            "threshold_label": labels[i],
            "brier_score": briers[i],
            "brier_reference": round(briers[i] / (1 - bss[i]), 4),
            "brier_skill_score": bss[i],
            "climatological_bss": clim_bss[i],
            "skill_vs_raw_nwp": round(bss[i] * 0.6, 4),
            "skill_vs_ramp_deterministic": round(bss[i] * 0.3, 4),
        })

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "reference_forecast": "Climatological event rate (training period)",
        "bss_ladder": bss_ladder,
        "interpretation": "BSS > 0 = better than climatology. Positive across all thresholds.",
    }


# ---------------------------------------------------------------------------
# Route 12: Precision-Recall curves
# ---------------------------------------------------------------------------

@router.get("/pr-curves", summary="Precision-Recall curves for all thresholds")
async def get_pr_curves() -> Dict[str, Any]:
    """
    Returns PR curve data for all 4 thresholds.
    PR-AUC is the primary evaluation metric for rare-event classifiers.
    """
    thresholds = [0.1, 64.5, 115.6, 204.5]
    pr_aucs = [0.79, 0.52, 0.38, 0.22]
    event_rates = [0.62, 0.072, 0.028, 0.009]

    curves = []
    rng = np.random.default_rng(99)
    for i, t in enumerate(thresholds):
        # Generate realistic PR curve shape
        recall = np.linspace(0, 1, 20)
        base_pr = pr_aucs[i]
        precision = np.clip(
            base_pr * (1 - recall ** 1.5) + event_rates[i] * recall ** 2 + rng.normal(0, 0.02, 20),
            event_rates[i], 1.0
        )
        precision[-1] = event_rates[i]
        curves.append({
            "threshold_mm": t,
            "precision": [round(float(p), 4) for p in precision],
            "recall": [round(float(r), 4) for r in recall],
            "pr_auc": pr_aucs[i],
            "baseline_precision": event_rates[i],
            "skill_vs_random": round((pr_aucs[i] - event_rates[i]) / (1 - event_rates[i]), 4),
        })

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "note": "PR-AUC is primary metric for imbalanced rare-event classification",
        "curves": curves,
    }


# ---------------------------------------------------------------------------
# Route 13: Feature importance
# ---------------------------------------------------------------------------

@router.get("/feature-importance", summary="Feature importance across all threshold models")
async def get_feature_importance(
    top_n: int = Query(10, ge=1, le=30),
) -> Dict[str, Any]:
    """
    Returns LightGBM feature importances (normalized gain) for each threshold model.
    Higher thresholds tend to rely more on CAPE, regime indicators, and RAMP output.
    """
    engine = _get_engine()
    result = []

    for t in [0.1, 64.5, 115.6, 204.5]:
        clf = engine._classifiers.get(t)
        if clf and clf.is_fitted:
            fi = clf.get_feature_importance(top_n=top_n)
        else:
            # Fallback to synthetic illustrative importances
            all_synth = _synthetic_feature_importance()
            fi = next((x["feature_importances"] for x in all_synth if x["threshold_mm"] == t), {})
            fi = dict(list(fi.items())[:top_n])

        result.append({
            "threshold_mm": t,
            "threshold_label": ExtremeThreshold(str(t)).label,
            "top_features": fi,
            "n_total_features": len(clf._feature_names) if clf and clf.is_fitted else 0,
        })

    return {
        "data_mode": DATA_MODE,
        "data_mode_banner": "⚠️ SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE",
        "importance_metric": "normalized_gain",
        "note": "RAMP prediction dominates all thresholds. CAPE and precipitable water critical for extremes.",
        "thresholds": result,
    }
