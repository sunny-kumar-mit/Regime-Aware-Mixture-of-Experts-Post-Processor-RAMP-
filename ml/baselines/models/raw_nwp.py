"""
RAMP Baseline 0: Raw NWP Precipitation
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.models.base import BaseBaselineModel


class RawNWPBaseline(BaseBaselineModel):
    """
    Baseline 0: Uncorrected raw Numerical Weather Prediction (NWP) rainfall.
    Serves as the primary reference benchmark against which all post-processing systems are evaluated.
    """

    def __init__(self, raw_rain_col: str = "raw_nwp_rainfall", version: str = "raw_nwp_v1") -> None:
        super().__init__(name="Raw_NWP", version=version)
        self.raw_rain_col = raw_rain_col
        self.is_fitted = True  # Non-parametric reference, requires no training
        self.fitted_split = "NONE (Reference)"
        self.metadata = {
            "model_type": "RAW_NWP",
            "description": "Uncorrected raw NWP rainfall benchmark",
            "correction_applied": False,
        }

    def fit(
        self,
        X: pd.DataFrame,
        y: Optional[np.ndarray | pd.Series] = None,
        split_label: str = "TRAIN",
    ) -> "RawNWPBaseline":
        """Reference baseline requires no fitting; validates feature columns for leakage."""
        self._validate_features(X, [self.raw_rain_col] if self.raw_rain_col in X.columns else None)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Extracts raw NWP precipitation. Enforces physical non-negativity (R >= 0.0).
        """
        if self.raw_rain_col not in X.columns:
            raise KeyError(f"Expected raw rainfall column '{self.raw_rain_col}' not found in input.")

        raw_values = X[self.raw_rain_col].fillna(0.0).values
        return self.enforce_physical_constraints(raw_values)
