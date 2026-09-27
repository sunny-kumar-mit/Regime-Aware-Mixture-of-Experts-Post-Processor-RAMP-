"""
Probability Calibration for RAMP Extreme Rainfall Models
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part N: Isotonic Regression & Platt Scaling Calibration Pipeline
Ensures forecast probabilities are strictly calibrated on VALIDATION data only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

logger = logging.getLogger(__name__)


def compute_ece_mce(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Tuple[float, float, List[Dict[str, float]]]:
    """
    Calculate Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
    and reliability diagram bin statistics.
    """
    if len(y_true) == 0:
        return 0.0, 0.0, []

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    ece = 0.0
    mce = 0.0
    bins_data = []

    total_samples = len(y_true)

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= low) & (y_prob <= high)
        else:
            mask = (y_prob >= low) & (y_prob < high)

        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            diff = abs(bin_acc - bin_conf)
            weight = bin_count / total_samples

            ece += weight * diff
            if diff > mce:
                mce = diff

            bins_data.append({
                "bin_idx": i,
                "bin_low": round(float(low), 3),
                "bin_high": round(float(high), 3),
                "bin_center": round(float(bin_centers[i]), 3),
                "sample_count": bin_count,
                "mean_predicted_prob": round(bin_conf, 4),
                "observed_frequency": round(bin_acc, 4),
                "calibration_gap": round(diff, 4),
            })
        else:
            bins_data.append({
                "bin_idx": i,
                "bin_low": round(float(low), 3),
                "bin_high": round(float(high), 3),
                "bin_center": round(float(bin_centers[i]), 3),
                "sample_count": 0,
                "mean_predicted_prob": None,
                "observed_frequency": None,
                "calibration_gap": None,
            })

    return round(float(ece), 4), round(float(mce), 4), bins_data


class ProbabilityCalibrator:
    """
    Calibrator supporting Isotonic Regression and Platt Scaling (Logistic Regression).
    MUST be fitted strictly on validation predictions.
    """

    def __init__(self, method: str = "isotonic"):
        if method not in ("isotonic", "platt", "none"):
            raise ValueError(f"Unknown calibration method: {method}")
        self.method = method
        self.calibrator = None
        self.is_fitted = False

    def fit(self, y_val_prob: np.ndarray, y_val_true: np.ndarray) -> "ProbabilityCalibrator":
        """Fit calibration mapping on validation set."""
        y_p = np.clip(np.asarray(y_val_prob, dtype=float), 0.0, 1.0)
        y_t = np.asarray(y_val_true, dtype=int)

        if len(np.unique(y_t)) < 2:
            logger.warning("Validation set has only 1 class. Calibration set to identity.")
            self.method = "none"
            self.is_fitted = True
            return self

        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self.calibrator.fit(y_p, y_t)
        elif self.method == "platt":
            # Platt scaling: logistic regression on logit or raw probabilities
            self.calibrator = LogisticRegression(C=1.0, solver="lbfgs")
            self.calibrator.fit(y_p.reshape(-1, 1), y_t)

        self.is_fitted = True
        return self

    def predict(self, y_prob: np.ndarray) -> np.ndarray:
        """Calibrate probabilities."""
        if not self.is_fitted or self.method == "none" or self.calibrator is None:
            return np.clip(np.asarray(y_prob, dtype=float), 0.0, 1.0)

        y_p = np.clip(np.asarray(y_prob, dtype=float), 0.0, 1.0)
        if self.method == "isotonic":
            cal = self.calibrator.predict(y_p)
        elif self.method == "platt":
            cal = self.calibrator.predict_proba(y_p.reshape(-1, 1))[:, 1]
        else:
            cal = y_p

        return np.clip(cal, 0.0, 1.0)
