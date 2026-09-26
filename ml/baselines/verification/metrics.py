"""
RAMP Meteorological Verification Metrics Engine
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Implements WMO and IMD standard continuous and categorical verification metrics:
  - Continuous: RMSE, MAE, Mean Bias, Pearson Correlation.
  - Categorical (at 0.1, 64.5, 115.6, 204.5 mm): Hits, Misses, False Alarms, Correct Negatives.
  - POD (Probability of Detection)
  - FAR (False Alarm Ratio)
  - CSI (Critical Success Index)
  - ETS (Equitable Threat Score)
  - Frequency Bias (FBIAS)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Canonical IMD rainfall thresholds (mm / 24h)
CANONICAL_THRESHOLDS: Dict[str, float] = {
    "rain_occurrence": 0.1,
    "heavy_rainfall": 64.5,
    "very_heavy_rainfall": 115.6,
    "extremely_heavy_rainfall": 204.5,
}


def calculate_continuous_metrics(
    predictions: np.ndarray | List[float],
    observations: np.ndarray | List[float],
) -> Dict[str, Optional[float]]:
    """
    Computes continuous verification metrics: RMSE, MAE, Mean Bias, Pearson R.
    """
    preds = np.asarray(predictions, dtype=float)
    obs = np.asarray(observations, dtype=float)

    if len(preds) == 0 or len(obs) == 0:
        return {
            "rmse": None,
            "mae": None,
            "mean_bias": None,
            "pearson_r": None,
            "sample_count": 0,
        }

    errors = preds - obs
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mae = float(np.mean(np.abs(errors)))
    bias = float(np.mean(errors))

    # Pearson correlation coefficient
    std_p = float(np.std(preds))
    std_o = float(np.std(obs))
    if std_p > 1e-6 and std_o > 1e-6:
        r = float(np.corrcoef(preds, obs)[0, 1])
    else:
        r = 0.0

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "mean_bias": round(bias, 4),
        "pearson_r": round(r, 4),
        "sample_count": len(preds),
    }


def calculate_contingency_table(
    predictions: np.ndarray | List[float],
    observations: np.ndarray | List[float],
    threshold: float,
) -> Dict[str, int]:
    """
    Computes 2x2 contingency table for an event defined by R >= threshold:
      - Hits (H): forecast >= threshold and observed >= threshold
      - Misses (M): forecast < threshold and observed >= threshold
      - False Alarms (FA): forecast >= threshold and observed < threshold
      - Correct Negatives (CN): forecast < threshold and observed < threshold
    """
    preds = np.asarray(predictions, dtype=float)
    obs = np.asarray(observations, dtype=float)

    pred_event = preds >= threshold
    obs_event = obs >= threshold

    hits = int(np.sum(pred_event & obs_event))
    misses = int(np.sum((~pred_event) & obs_event))
    false_alarms = int(np.sum(pred_event & (~obs_event)))
    correct_negatives = int(np.sum((~pred_event) & (~obs_event)))

    return {
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "correct_negatives": correct_negatives,
        "total": len(preds),
    }


def calculate_pod(hits: int, misses: int) -> Optional[float]:
    """
    Probability of Detection: POD = H / (H + M).
    Returns None if no observed events occurred (H + M == 0).
    """
    denom = hits + misses
    if denom == 0:
        return None
    return round(float(hits / denom), 4)


def calculate_far(hits: int, false_alarms: int) -> Optional[float]:
    """
    False Alarm Ratio: FAR = FA / (H + FA).
    Returns None if no forecast events occurred (H + FA == 0).
    """
    denom = hits + false_alarms
    if denom == 0:
        return None
    return round(float(false_alarms / denom), 4)


def calculate_csi(hits: int, misses: int, false_alarms: int) -> Optional[float]:
    """
    Critical Success Index (Threat Score): CSI = H / (H + M + FA).
    Returns None if no events forecast or observed.
    """
    denom = hits + misses + false_alarms
    if denom == 0:
        return None
    return round(float(hits / denom), 4)


def calculate_ets(
    hits: int,
    misses: int,
    false_alarms: int,
    correct_negatives: int,
) -> Optional[float]:
    """
    Equitable Threat Score (Gilbert Skill Score):
      Hits_random = (H + M) * (H + FA) / N
      ETS = (H - Hits_random) / (H + M + FA - Hits_random)
    Ranges from -1/3 to 1. 0 indicates no skill beyond random chance.
    """
    n = hits + misses + false_alarms + correct_negatives
    if n == 0:
        return None

    hits_random = (hits + misses) * (hits + false_alarms) / n
    denom = (hits + misses + false_alarms) - hits_random

    if denom <= 0:
        return 0.0

    ets = (hits - hits_random) / denom
    return round(float(ets), 4)


def calculate_categorical_metrics_for_threshold(
    predictions: np.ndarray | List[float],
    observations: np.ndarray | List[float],
    threshold: float,
) -> Dict[str, Any]:
    """
    Computes complete categorical verification package for a single threshold.
    """
    table = calculate_contingency_table(predictions, observations, threshold)
    h = table["hits"]
    m = table["misses"]
    fa = table["false_alarms"]
    cn = table["correct_negatives"]

    pod = calculate_pod(h, m)
    far = calculate_far(h, fa)
    csi = calculate_csi(h, m, fa)
    ets = calculate_ets(h, m, fa, cn)
    fbias = round(float((h + fa) / (h + m)), 4) if (h + m) > 0 else None

    return {
        "threshold_mm": threshold,
        "contingency_table": table,
        "pod": pod,
        "far": far,
        "csi": csi,
        "ets": ets,
        "fbias": fbias,
    }


def calculate_all_threshold_metrics(
    predictions: np.ndarray | List[float],
    observations: np.ndarray | List[float],
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes categorical metrics across all canonical IMD thresholds.
    """
    target_thresholds = thresholds or CANONICAL_THRESHOLDS
    results = {}

    for name, thresh in target_thresholds.items():
        results[name] = calculate_categorical_metrics_for_threshold(
            predictions, observations, thresh
        )

    return results
