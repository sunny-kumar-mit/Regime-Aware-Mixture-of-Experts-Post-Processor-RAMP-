"""
RAMP Baseline 3: Global Machine Learning Post-Processor (LightGBM Regression)
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.models.base import BaseBaselineModel
from ml.dataset.leakage_guard import DataLeakageError


class GlobalMLPostProcessor(BaseBaselineModel):
    """
    Baseline 3: Global Machine Learning Rainfall Post-Processor.
    Trains a non-linear gradient-boosted decision tree regressor (LightGBM)
    across all weather states without regime-specific conditioning.
    Target: observed_rainfall_mm (with log1p transformation for zero-inflated skewness).
    Enforces strict baseline leakage isolation: zero target leakage, zero regime contamination.
    """

    DEFAULT_FEATURE_COLUMNS: List[str] = [
        "raw_nwp_rainfall",
        "lead_time_hours",
        "u850",
        "v850",
        "wind_speed_850",
        "wind_direction_850",
        "mslp",
        "mslp_anomaly",
        "temperature",
        "relative_humidity",
        "precipitable_water",
        "cape",
        "geopotential_height",
        "rainfall_mean_3x3",
        "rainfall_max_3x3",
        "rainfall_std_3x3",
        "elevation",
        "distance_to_coast",
        "monsoon",
        "winter",
        "pre_monsoon",
        "post_monsoon",
        "day_of_year_sin",
        "day_of_year_cos",
        "valid_hour_sin",
        "valid_hour_cos",
        "latitude",
        "longitude",
    ]

    def __init__(
        self,
        feature_columns: Optional[List[str]] = None,
        use_log1p_target: bool = True,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        random_state: int = 42,
        version: str = "global_lgbm_v1",
    ) -> None:
        super().__init__(name="Global_LightGBM", version=version)
        self.feature_columns = feature_columns or self.DEFAULT_FEATURE_COLUMNS
        self.use_log1p_target = use_log1p_target
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state

        self.feature_importances: Dict[str, float] = {}

        try:
            import lightgbm as lgb
            self.model = lgb.LGBMRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                random_state=self.random_state,
                verbosity=-1,
            )
        except ImportError:
            from sklearn.ensemble import HistGradientBoostingRegressor
            self.model = HistGradientBoostingRegressor(
                max_iter=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                random_state=self.random_state,
            )

    def fit(
        self,
        X: pd.DataFrame,
        y: np.ndarray | pd.Series,
        split_label: str = "TRAIN",
    ) -> "GlobalMLPostProcessor":
        """
        Fits global LightGBM model strictly on the TRAIN partition.
        Fails loudly if test or validation observations are provided.
        """
        if split_label != "TRAIN":
            raise DataLeakageError(
                f"[LEAKAGE VIOLATION] GlobalMLPostProcessor cannot be fitted on split '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )

        # Audit features against target leakage AND regime contamination
        valid_cols = [c for c in self.feature_columns if c in X.columns]
        self._validate_features(X, valid_cols)
        self.feature_columns = valid_cols

        X_mat = X[self.feature_columns].fillna(0.0).values
        y_vals = np.asarray(y, dtype=float)

        # Target transformation
        y_train = np.log1p(np.maximum(0.0, y_vals)) if self.use_log1p_target else y_vals

        self.model.fit(X_mat, y_train)

        # Compute feature importances
        if hasattr(self.model, "feature_importances_"):
            raw_imp = self.model.feature_importances_.astype(float)
            total = float(np.sum(raw_imp)) if np.sum(raw_imp) > 0 else 1.0
            self.feature_importances = {
                feat: round(float(raw_imp[i] / total), 4)
                for i, feat in enumerate(self.feature_columns)
            }

        self.is_fitted = True
        self.fitted_split = split_label
        self.metadata = {
            "model_type": "GLOBAL_LIGHTGBM",
            "use_log1p_target": self.use_log1p_target,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "feature_count": len(self.feature_columns),
            "features": list(self.feature_columns),
            "fitted_split": self.fitted_split,
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predicts post-processed rainfall.
        Inverts log1p transformation if enabled, and enforces R >= 0.0 mm.
        """
        if not self.is_fitted:
            raise RuntimeError("GlobalMLPostProcessor must be fitted before predict() is called.")

        valid_cols = [c for c in self.feature_columns if c in X.columns]
        self._validate_features(X, valid_cols)

        # Prepare matrix with missing columns filled with 0.0
        X_df = pd.DataFrame(index=X.index)
        for col in self.feature_columns:
            if col in X.columns:
                X_df[col] = X[col].fillna(0.0)
            else:
                X_df[col] = 0.0

        raw_preds = self.model.predict(X_df.values)

        if self.use_log1p_target:
            # Inverse log1p: expm1(y) = exp(y) - 1
            preds = np.expm1(raw_preds)
        else:
            preds = raw_preds

        return self.enforce_physical_constraints(preds)
