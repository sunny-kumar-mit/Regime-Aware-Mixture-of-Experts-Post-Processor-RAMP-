"""
RAMP Baseline 1: Mean Bias Correction (Linear Additive Bias)
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.models.base import BaseBaselineModel
from ml.dataset.leakage_guard import DataLeakageError


class MeanBiasCorrector(BaseBaselineModel):
    """
    Baseline 1: Classical Additive Mean Bias Correction.
    Calculates empirical mean error (R_obs - R_nwp) strictly on TRAIN data.
    Supports lead-time-specific bias correction with graceful fallback to global bias.
    Enforces physical non-negativity (R_corrected >= 0.0 mm).
    """

    def __init__(
        self,
        raw_rain_col: str = "raw_nwp_rainfall",
        lead_time_col: str = "lead_time_hours",
        min_samples_per_lead: int = 10,
        version: str = "mean_bias_v1",
    ) -> None:
        super().__init__(name="Mean_Bias_Correction", version=version)
        self.raw_rain_col = raw_rain_col
        self.lead_time_col = lead_time_col
        self.min_samples_per_lead = min_samples_per_lead

        self.global_bias: float = 0.0
        self.lead_time_biases: Dict[int, float] = {}
        self.lead_time_counts: Dict[int, int] = {}
        self.total_train_samples: int = 0

    def fit(
        self,
        X: pd.DataFrame,
        y: np.ndarray | pd.Series,
        split_label: str = "TRAIN",
    ) -> "MeanBiasCorrector":
        """
        Fits mean bias correction strictly on the TRAIN partition.
        Fails loudly if test or validation observations are provided.
        """
        if split_label != "TRAIN":
            raise DataLeakageError(
                f"[LEAKAGE VIOLATION] MeanBiasCorrector cannot be fitted on split '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )

        self._validate_features(X, [self.raw_rain_col, self.lead_time_col] if self.raw_rain_col in X.columns else None)

        y_obs = np.asarray(y, dtype=float)
        nwp = X[self.raw_rain_col].fillna(0.0).values.astype(float)
        errors = y_obs - nwp

        self.total_train_samples = len(y_obs)
        self.global_bias = float(np.mean(errors))

        # Calculate lead-time-stratified biases
        self.lead_time_biases = {}
        self.lead_time_counts = {}

        if self.lead_time_col in X.columns:
            leads = X[self.lead_time_col].values
            unique_leads = np.unique(leads)

            for ld in unique_leads:
                mask = leads == ld
                count = int(np.sum(mask))
                self.lead_time_counts[int(ld)] = count

                if count >= self.min_samples_per_lead:
                    self.lead_time_biases[int(ld)] = float(np.mean(errors[mask]))
                else:
                    # Fallback to global bias
                    self.lead_time_biases[int(ld)] = self.global_bias

        self.is_fitted = True
        self.fitted_split = split_label
        self.metadata = {
            "model_type": "MEAN_BIAS",
            "global_bias_mm": round(self.global_bias, 4),
            "lead_time_biases_mm": {str(k): round(v, 4) for k, v in self.lead_time_biases.items()},
            "lead_time_counts": {str(k): v for k, v in self.lead_time_counts.items()},
            "train_samples": self.total_train_samples,
            "fitted_split": self.fitted_split,
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Applies additive bias correction: R_corrected = max(0, R_nwp + bias).
        Uses lead-time-specific bias when available, falling back to global bias.
        """
        if not self.is_fitted:
            raise RuntimeError("MeanBiasCorrector must be fitted before predict() is called.")

        nwp = X[self.raw_rain_col].fillna(0.0).values.astype(float)
        n = len(nwp)
        corrected = np.zeros(n, dtype=float)

        if self.lead_time_col in X.columns and self.lead_time_biases:
            leads = X[self.lead_time_col].values
            for i in range(n):
                ld = int(leads[i]) if not pd.isna(leads[i]) else -1
                bias_val = self.lead_time_biases.get(ld, self.global_bias)
                corrected[i] = nwp[i] + bias_val
        else:
            corrected = nwp + self.global_bias

        return self.enforce_physical_constraints(corrected)
