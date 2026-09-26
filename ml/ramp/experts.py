"""
RAMP Regime-Specific Rainfall Post-Processing Experts
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Implements specialized LightGBM regression experts for each of the 7 canonical
weather regimes:
  - ACTIVE_MONSOON
  - BREAK_MONSOON
  - LOW_DEPRESSION
  - COASTAL
  - OROGRAPHIC
  - WESTERN_DISTURBANCE
  - TRANSITION_OTHER

Each expert models regime-specific precipitation error dynamics using physical
NWP predictors from Phase 3, predicting log1p-transformed rainfall.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.dataset.leakage_guard import DataLeakageError, audit_ramp_features
from ml.regimes.definitions import WeatherRegime


class RegimeExpert:
    """
    Specialized rainfall post-processing regression expert for a single meteorological regime.
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
        regime: WeatherRegime | str,
        feature_columns: Optional[List[str]] = None,
        use_log1p_target: bool = True,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        num_leaves: int = 24,
        min_child_samples: int = 5,
        random_state: int = 42,
        min_samples_to_train: int = 5,
        version: str = "v1.0.0",
    ) -> None:
        self.regime = WeatherRegime(regime) if isinstance(regime, str) else regime
        self.regime_name = self.regime.value
        self.feature_columns = feature_columns or self.DEFAULT_FEATURE_COLUMNS
        self.use_log1p_target = use_log1p_target
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.random_state = random_state
        self.min_samples_to_train = min_samples_to_train
        self.version = version

        self.is_fitted: bool = False
        self.status: str = "INITIALIZED"  # "TRAINED" or "INSUFFICIENT_DATA"
        self.train_sample_count: int = 0
        self.feature_importances: Dict[str, float] = {}

        try:
            import lightgbm as lgb
            self.model = lgb.LGBMRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                num_leaves=self.num_leaves,
                min_child_samples=self.min_child_samples,
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
        sample_weight: Optional[np.ndarray | pd.Series] = None,
        split_label: str = "TRAIN",
    ) -> "RegimeExpert":
        """
        Fits the specialized expert on regime-assigned training samples.
        Fails loudly if fitted on validation or test splits.
        """
        if split_label != "TRAIN":
            raise DataLeakageError(
                f"[LEAKAGE VIOLATION] RegimeExpert for '{self.regime_name}' cannot be fitted on '{split_label}'. "
                "Must be fitted strictly on 'TRAIN'."
            )

        avail_cols = [c for c in self.feature_columns if c in X.columns]
        if not avail_cols:
            avail_cols = [c for c in X.columns if c not in ["sample_id", "forecast_valid_time", "split"]]

        audit_ramp_features(avail_cols)

        self.feature_columns = avail_cols
        X_train = pd.DataFrame(index=X.index)
        for col in avail_cols:
            X_train[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0).astype(float)
        y_train = np.asarray(y, dtype=float)

        self.train_sample_count = len(X_train)

        # Check sample threshold
        if self.train_sample_count < self.min_samples_to_train:
            self.status = "INSUFFICIENT_DATA"
            self.is_fitted = False
            return self

        # Handle log1p transformation for skewed precipitation
        if self.use_log1p_target:
            y_fit = np.log1p(np.maximum(y_train, 0.0))
        else:
            y_fit = np.maximum(y_train, 0.0)

        # Fit model
        fit_params: Dict[str, Any] = {}
        if sample_weight is not None:
            fit_params["sample_weight"] = np.asarray(sample_weight, dtype=float)

        self.model.fit(X_train, y_fit, **fit_params)
        self.is_fitted = True
        self.status = "TRAINED"

        # Extract feature importances
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            total = float(np.sum(importances))
            if total > 0:
                self.feature_importances = {
                    col: round(float(imp / total), 4)
                    for col, imp in zip(avail_cols, importances)
                }
            else:
                self.feature_importances = {col: 0.0 for col in avail_cols}

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predicts post-processed rainfall in millimeters for the given features.
        Enforces physical non-negativity (R >= 0.0 mm).
        """
        if not self.is_fitted:
            raise RuntimeError(
                f"RegimeExpert for '{self.regime_name}' is not fitted (status: {self.status}). "
                "Use fallback mechanism."
            )

        avail_cols = [c for c in self.feature_columns if c in X.columns]
        audit_ramp_features(avail_cols)
        X_pred = pd.DataFrame(index=X.index)
        for col in avail_cols:
            X_pred[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0).astype(float)

        raw_preds = self.model.predict(X_pred)

        if self.use_log1p_target:
            preds_mm = np.expm1(raw_preds)
        else:
            preds_mm = raw_preds

        # Strict physical non-negativity constraint
        return np.maximum(preds_mm, 0.0)

    def predict_batch(self, X: pd.DataFrame) -> np.ndarray:
        return self.predict(X)

    def metadata(self) -> Dict[str, Any]:
        """Returns expert model metadata dictionary."""
        return {
            "regime": self.regime_name,
            "version": self.version,
            "status": self.status,
            "is_fitted": self.is_fitted,
            "train_sample_count": self.train_sample_count,
            "use_log1p_target": self.use_log1p_target,
            "hyperparameters": {
                "n_estimators": self.n_estimators,
                "learning_rate": self.learning_rate,
                "max_depth": self.max_depth,
                "num_leaves": self.num_leaves,
                "min_child_samples": self.min_child_samples,
                "random_state": self.random_state,
            },
            "feature_columns": self.feature_columns,
            "top_features": sorted(
                self.feature_importances.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }


# Specialized Subclasses
class ActiveMonsoonExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.ACTIVE_MONSOON, **kwargs)


class BreakMonsoonExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.BREAK_MONSOON, **kwargs)


class LowDepressionExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.LOW_DEPRESSION, **kwargs)


class CoastalExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.COASTAL, **kwargs)


class OrographicExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.OROGRAPHIC, **kwargs)


class WesternDisturbanceExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.WESTERN_DISTURBANCE, **kwargs)


class TransitionOtherExpert(RegimeExpert):
    def __init__(self, **kwargs) -> None:
        super().__init__(regime=WeatherRegime.TRANSITION_OTHER, **kwargs)
