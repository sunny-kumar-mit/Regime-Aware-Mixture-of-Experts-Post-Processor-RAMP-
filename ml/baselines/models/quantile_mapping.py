"""
RAMP Baseline 2: Empirical Quantile Mapping (Precipitation-Aware EQM)
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import interpolate

from ml.baselines.models.base import BaseBaselineModel
from ml.dataset.leakage_guard import DataLeakageError


class EmpiricalQuantileMapper(BaseBaselineModel):
    """
    Baseline 2: Precipitation-Aware Empirical Quantile Mapping (EQM).
    Fits empirical cumulative distribution functions F_nwp and F_obs strictly on TRAIN data.
    Explicitly separates dry occurrence (R < threshold) from positive rainfall distribution.
    Employs linear tail extrapolation to preserve extreme rainfall tails without artificial clipping.
    """

    def __init__(
        self,
        raw_rain_col: str = "raw_nwp_rainfall",
        rain_threshold: float = 0.1,
        n_quantiles: int = 100,
        extrapolation_policy: str = "linear",
        version: str = "quantile_mapping_v1",
    ) -> None:
        super().__init__(name="Empirical_Quantile_Mapping", version=version)
        self.raw_rain_col = raw_rain_col
        self.rain_threshold = rain_threshold
        self.n_quantiles = n_quantiles
        self.extrapolation_policy = extrapolation_policy

        # Fitted parameters
        self.p_dry_nwp: float = 0.0
        self.p_dry_obs: float = 0.0
        self.nwp_wet_quantiles: np.ndarray = np.array([])
        self.obs_wet_quantiles: np.ndarray = np.array([])
        self.quantile_levels: np.ndarray = np.array([])
        self.tail_ratio: float = 1.0
        self.train_samples: int = 0
        self.train_wet_samples: int = 0

    def fit(
        self,
        X: pd.DataFrame,
        y: np.ndarray | pd.Series,
        split_label: str = "TRAIN",
    ) -> "EmpiricalQuantileMapper":
        """
        Fits empirical quantiles strictly on TRAIN observations and NWP predictors.
        Fails loudly if fitted on validation or test splits.
        """
        if split_label != "TRAIN":
            raise DataLeakageError(
                f"[LEAKAGE VIOLATION] EmpiricalQuantileMapper cannot be fitted on split '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )

        self._validate_features(X, [self.raw_rain_col] if self.raw_rain_col in X.columns else None)

        y_obs = np.asarray(y, dtype=float)
        nwp = X[self.raw_rain_col].fillna(0.0).values.astype(float)

        self.train_samples = len(y_obs)

        # 1. Zero-rain / dry occurrence separation
        dry_nwp_mask = nwp < self.rain_threshold
        dry_obs_mask = y_obs < self.rain_threshold

        self.p_dry_nwp = float(np.mean(dry_nwp_mask))
        self.p_dry_obs = float(np.mean(dry_obs_mask))

        nwp_wet = nwp[~dry_nwp_mask]
        obs_wet = y_obs[~dry_obs_mask]
        self.train_wet_samples = len(nwp_wet)

        if len(nwp_wet) == 0 or len(obs_wet) == 0:
            # Fallback if insufficient wet events
            self.quantile_levels = np.linspace(0.0, 1.0, 10)
            self.nwp_wet_quantiles = np.zeros(10)
            self.obs_wet_quantiles = np.zeros(10)
            self.tail_ratio = 1.0
        else:
            # Compute empirical quantiles on wet events
            probs = np.linspace(0.01, 0.99, self.n_quantiles)
            self.quantile_levels = probs
            self.nwp_wet_quantiles = np.quantile(nwp_wet, probs)
            self.obs_wet_quantiles = np.quantile(obs_wet, probs)

            # Ensure strict monotonicity for interpolation
            self.nwp_wet_quantiles = np.maximum.accumulate(self.nwp_wet_quantiles)
            self.obs_wet_quantiles = np.maximum.accumulate(self.obs_wet_quantiles)

            # Calculate upper tail scaling ratio for linear tail extrapolation
            top_nwp = float(np.quantile(nwp_wet, 0.95))
            top_obs = float(np.quantile(obs_wet, 0.95))
            self.tail_ratio = (top_obs / top_nwp) if top_nwp > 0.1 else 1.0

        self.is_fitted = True
        self.fitted_split = split_label
        self.metadata = {
            "model_type": "QUANTILE_MAPPING",
            "rain_threshold_mm": self.rain_threshold,
            "extrapolation_policy": self.extrapolation_policy,
            "train_samples": self.train_samples,
            "train_wet_samples": self.train_wet_samples,
            "p_dry_nwp": round(self.p_dry_nwp, 4),
            "p_dry_obs": round(self.p_dry_obs, 4),
            "tail_ratio": round(self.tail_ratio, 4),
            "p95_nwp": round(float(np.quantile(nwp, 0.95)), 2) if len(nwp) else 0.0,
            "p95_obs": round(float(np.quantile(y_obs, 0.95)), 2) if len(y_obs) else 0.0,
            "fitted_split": self.fitted_split,
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Maps forecast precipitation through the empirical CDF transfer function:
          R_corrected = F_obs^{-1}(F_nwp(R_nwp))
        Applies dry frequency correction and linear tail extrapolation for extreme events.
        """
        if not self.is_fitted:
            raise RuntimeError("EmpiricalQuantileMapper must be fitted before predict() is called.")

        nwp = X[self.raw_rain_col].fillna(0.0).values.astype(float)
        n = len(nwp)
        corrected = np.zeros(n, dtype=float)

        if len(self.nwp_wet_quantiles) < 2:
            return self.enforce_physical_constraints(nwp)

        # Cutoff threshold adjusted for NWP dry bias / over-frequency
        # If NWP predicts dry, keep dry
        is_dry = nwp < self.rain_threshold
        corrected[is_dry] = 0.0

        # Wet cases
        wet_indices = np.where(~is_dry)[0]
        wet_nwp = nwp[wet_indices]

        # Use piecewise linear interpolation between empirical quantiles
        max_nwp_q = self.nwp_wet_quantiles[-1]
        max_obs_q = self.obs_wet_quantiles[-1]
        min_nwp_q = self.nwp_wet_quantiles[0]
        min_obs_q = self.obs_wet_quantiles[0]

        # In-distribution interpolation
        in_range_mask = (wet_nwp >= min_nwp_q) & (wet_nwp <= max_nwp_q)
        interp_vals = np.interp(
            wet_nwp[in_range_mask],
            self.nwp_wet_quantiles,
            self.obs_wet_quantiles,
        )
        corrected[wet_indices[in_range_mask]] = interp_vals

        # Below lowest wet quantile
        low_mask = wet_nwp < min_nwp_q
        corrected[wet_indices[low_mask]] = min_obs_q * (wet_nwp[low_mask] / max(0.01, min_nwp_q))

        # Extreme tail extrapolation (values exceeding max training quantile)
        high_mask = wet_nwp > max_nwp_q
        if np.any(high_mask):
            excess = wet_nwp[high_mask] - max_nwp_q
            if self.extrapolation_policy == "linear":
                # Linear tail extrapolation preserving extreme deluges
                corrected[wet_indices[high_mask]] = max_obs_q + excess * self.tail_ratio
            else:
                # Constant nearest endpoint tail
                corrected[wet_indices[high_mask]] = max_obs_q

        return self.enforce_physical_constraints(corrected)
