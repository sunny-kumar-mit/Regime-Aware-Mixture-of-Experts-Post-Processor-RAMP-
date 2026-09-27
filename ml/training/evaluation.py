"""
RAMP Scientific Verification & Model Comparison Suite
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Parts P, Q, R, S, T:
- Lead-Time Evaluation (6h, 12h, 18h, 24h, 36h, 48h, 72h, etc.)
- Weather Regime-Stratified Evaluation
- Categorical Threshold Verification (POD, FAR, CSI, ETS, Frequency Bias)
- Spatial Verification (if coordinates present)
- Transparent Objective Model Comparison Table (No subjective ranks or tiers)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.training.global_model import compute_continuous_metrics

logger = logging.getLogger(__name__)

VERIFICATION_THRESHOLDS = [0.1, 64.5, 115.6, 204.5]


def compute_contingency_table(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float,
) -> Dict[str, Any]:
    """
    Compute 2x2 contingency table and standard WMO / IMD verification scores:
    POD, FAR, CSI (Threat Score), ETS (Equitable Threat Score), Frequency Bias.
    """
    obs_bin = (y_true >= threshold).astype(bool)
    pred_bin = (y_pred >= threshold).astype(bool)

    hits = int(np.sum(obs_bin & pred_bin))
    false_alarms = int(np.sum(~obs_bin & pred_bin))
    misses = int(np.sum(obs_bin & ~pred_bin))
    correct_negatives = int(np.sum(~obs_bin & ~pred_bin))
    total = len(y_true)

    # POD: Probability of Detection = H / (H + M)
    denom_pod = hits + misses
    pod = float(hits / denom_pod) if denom_pod > 0 else 0.0

    # FAR: False Alarm Ratio = F / (H + F)
    denom_far = hits + false_alarms
    far = float(false_alarms / denom_far) if denom_far > 0 else 0.0

    # CSI: Critical Success Index = H / (H + F + M)
    denom_csi = hits + false_alarms + misses
    csi = float(hits / denom_csi) if denom_csi > 0 else 0.0

    # Frequency Bias = (H + F) / (H + M)
    freq_bias = float(denom_far / denom_pod) if denom_pod > 0 else 1.0

    # ETS: Equitable Threat Score = (H - Hr) / (H + F + M - Hr)
    # where Hr = (H + M) * (H + F) / N
    hr = float((denom_pod * denom_far) / total) if total > 0 else 0.0
    denom_ets = denom_csi - hr
    ets = float((hits - hr) / denom_ets) if abs(denom_ets) > 1e-6 else 0.0

    return {
        "threshold_mm": threshold,
        "contingency_matrix": {
            "hits": hits,
            "false_alarms": false_alarms,
            "misses": misses,
            "correct_negatives": correct_negatives,
            "total_samples": total,
        },
        "pod": round(pod, 4),
        "far": round(far, 4),
        "csi": round(csi, 4),
        "ets": round(ets, 4),
        "bias_score": round(freq_bias, 4),
    }


def evaluate_lead_times(
    df_test: pd.DataFrame,
    y_true_col: str = "observed_rainfall",
    pred_cols: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Evaluate continuous and threshold metrics stratified by lead time hours.
    Only includes lead times actually present in the dataset (Part P).
    """
    if "lead_time_hours" not in df_test.columns:
        return {"status": "LEAD_TIMES_NOT_IN_DATASET"}

    unique_leads = sorted(df_test["lead_time_hours"].dropna().unique().tolist())
    if not unique_leads:
        return {"status": "NO_LEAD_TIMES_FOUND"}

    preds = pred_cols or {"raw_nwp": "precip_nwp_raw"}
    lead_metrics = {}

    for lead in unique_leads:
        subset = df_test[df_test["lead_time_hours"] == lead]
        if len(subset) == 0:
            continue

        y_true = np.asarray(subset[y_true_col], dtype=float)
        lead_entry = {"sample_count": len(subset), "models": {}}

        for model_name, col in preds.items():
            if col in subset.columns:
                y_pred = np.asarray(subset[col], dtype=float)
                cont = compute_continuous_metrics(y_true, y_pred)
                lead_entry["models"][model_name] = cont

        lead_metrics[f"{int(lead)}h"] = lead_entry

    return {
        "available_lead_times": [int(l) for l in unique_leads],
        "lead_time_metrics": lead_metrics,
    }


def evaluate_regimes(
    df_test: pd.DataFrame,
    y_true_col: str = "observed_rainfall",
    pred_cols: Optional[Dict[str, str]] = None,
    regime_col: str = "regime",
) -> Dict[str, Any]:
    """
    Evaluate models stratified by weather regime (Part Q).
    """
    if regime_col not in df_test.columns:
        return {"status": "REGIME_COL_NOT_IN_DATASET"}

    regimes = sorted(df_test[regime_col].dropna().unique().tolist())
    preds = pred_cols or {"raw_nwp": "precip_nwp_raw"}
    regime_metrics = {}

    for r in regimes:
        subset = df_test[df_test[regime_col] == r]
        count = len(subset)
        if count < 5:
            regime_metrics[str(r)] = {
                "sample_count": count,
                "status": "SAMPLE_LIMITED",
            }
            continue

        y_true = np.asarray(subset[y_true_col], dtype=float)
        regime_entry = {"sample_count": count, "models": {}}

        for model_name, col in preds.items():
            if col in subset.columns:
                y_pred = np.asarray(subset[col], dtype=float)
                regime_entry["models"][model_name] = compute_continuous_metrics(y_true, y_pred)

        regime_metrics[str(r)] = regime_entry

    return {"regimes": regime_metrics}


def evaluate_threshold_suite(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    thresholds: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Evaluate categorical contingency metrics across all IMD thresholds (Part R)."""
    thresh_list = thresholds or VERIFICATION_THRESHOLDS
    results = {}
    for t in thresh_list:
        results[f"ge_{str(t).replace('.', 'p')}mm"] = compute_contingency_table(y_true, y_pred, t)
    return results


def build_model_comparison_table(
    models_predictions: Dict[str, np.ndarray],
    y_true: np.ndarray,
    dataset_version: str = "ramp_dataset_real_v1.0.0",
    lead_time: str = "ALL",
) -> List[Dict[str, Any]]:
    """
    Create objective model comparison table (Part T).
    No subjective rankings, tiers, or winners. Purely objective metrics.
    """
    comparison = []

    for model_name, y_pred in models_predictions.items():
        cont = compute_continuous_metrics(y_true, y_pred)
        # Use >= 0.1 mm for POD/FAR/CSI in general table
        cat_0p1 = compute_contingency_table(y_true, y_pred, 0.1)

        row = {
            "model": model_name,
            "dataset": dataset_version,
            "lead_time": lead_time,
            "mae": cont["mae"],
            "rmse": cont["rmse"],
            "bias": cont["bias"],
            "correlation": cont["correlation"],
            "r2": cont["r2"],
            "pod_0p1mm": cat_0p1["pod"],
            "far_0p1mm": cat_0p1["far"],
            "csi_0p1mm": cat_0p1["csi"],
            "bias_score_0p1mm": cat_0p1["bias_score"],
        }
        comparison.append(row)

    return comparison
