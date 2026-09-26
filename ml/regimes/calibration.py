"""
RAMP Multi-Class Probability Calibration Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Calibrates raw ML classifier posteriors:
  - Isotonic Regression or Platt Sigmoid calibration.
  - Fitted strictly on the VALIDATION split (never on test data).
  - Enforces sum(probabilities) == 1.0 post-calibration via softmax/renormalization.
  - Computes multi-class Brier score and log loss diagnostics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from ml.regimes.definitions import REGIME_ORDER


class RegimeCalibrator:
    """
    Fits and applies probability calibration strictly on validation data.
    """

    def __init__(self, method: str = "isotonic") -> None:
        self.method = method.lower()
        self.calibrators: List[Any] = []
        self.is_fitted: bool = False
        self.fitted_split: Optional[str] = None

    def fit(
        self,
        val_probs: np.ndarray,
        val_labels: np.ndarray,
        split_label: str = "VALIDATION",
    ) -> "RegimeCalibrator":
        """
        Fits 1-vs-rest calibrators per regime class strictly on the validation partition.
        val_probs: shape (N, 7)
        val_labels: shape (N,) integer class indices (0..6)
        """
        if split_label != "VALIDATION":
            raise ValueError(
                f"Data Leakage Violation: Calibration cannot be fitted on split '{split_label}'. "
                "Must be fitted strictly on 'VALIDATION'."
            )

        n_classes = val_probs.shape[1]
        self.calibrators = []

        for k in range(n_classes):
            binary_target = (val_labels == k).astype(int)
            p_k = val_probs[:, k]

            if self.method == "isotonic":
                cal = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
                cal.fit(p_k, binary_target)
            else:
                # Platt scaling (logistic sigmoid)
                cal = LogisticRegression(C=1.0, solver="lbfgs")
                cal.fit(p_k.reshape(-1, 1), binary_target)

            self.calibrators.append(cal)

        self.is_fitted = True
        self.fitted_split = split_label
        return self

    def calibrate(self, probs: np.ndarray) -> np.ndarray:
        """
        Applies calibration and normalizes so rows strictly sum to 1.0.
        """
        if not self.is_fitted:
            # If not fitted, return cleanly normalized input probabilities
            p = np.array(probs, dtype=float)
            return p / np.sum(p, axis=-1, keepdims=True)

        probs_mat = np.array(probs, dtype=float)
        single_dim = probs_mat.ndim == 1
        if single_dim:
            probs_mat = probs_mat.reshape(1, -1)

        calibrated_mat = np.zeros_like(probs_mat)

        for k, cal in enumerate(self.calibrators):
            p_k = probs_mat[:, k]
            if self.method == "isotonic":
                calibrated_mat[:, k] = cal.predict(p_k)
            else:
                calibrated_mat[:, k] = cal.predict_proba(p_k.reshape(-1, 1))[:, 1]

        # Renormalize to ensure sum == 1.0 across the 7 regimes
        row_sums = np.sum(calibrated_mat, axis=1, keepdims=True)
        # Avoid division by zero
        row_sums = np.where(row_sums < 1e-9, 1.0, row_sums)
        normalized = np.clip(calibrated_mat / row_sums, 0.0, 1.0)
        # Final pass normalization to guarantee exact sum == 1.0
        normalized = normalized / np.sum(normalized, axis=1, keepdims=True)

        return normalized[0] if single_dim else normalized

    @staticmethod
    def evaluate_calibration(
        probs: np.ndarray,
        labels: np.ndarray,
        n_classes: int = 7,
    ) -> Dict[str, float]:
        """
        Calculates multi-class Brier score and log loss.
        """
        eps = 1e-9
        N = len(labels)
        if N == 0:
            return {"brier_score": 0.0, "log_loss": 0.0}

        # One-hot encode labels
        one_hot = np.zeros((N, n_classes), dtype=float)
        for i, lbl in enumerate(labels):
            if 0 <= lbl < n_classes:
                one_hot[i, int(lbl)] = 1.0

        p = np.clip(probs, eps, 1.0)
        p = p / np.sum(p, axis=1, keepdims=True)

        # Brier score: mean squared difference across all classes
        brier = float(np.mean(np.sum((p - one_hot) ** 2, axis=1)))

        # Multi-class log loss
        log_loss = -float(np.mean(np.sum(one_hot * np.log(p), axis=1)))

        return {
            "brier_score": round(brier, 4),
            "log_loss": round(log_loss, 4),
        }
