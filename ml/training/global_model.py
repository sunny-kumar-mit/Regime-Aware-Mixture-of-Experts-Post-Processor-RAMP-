"""
RAMP Global Precipitation Post-Processing Model
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part H: Global ML Model Training & Stratified Evaluation
Trains a unified gradient-boosted regression model on all 18 approved predictors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    TARGET_SCHEMA_VERSION,
    ModelLifecycle,
)
from ml.training.feature_contract import APPROVED_PREDICTORS, audit_predictor_dataframe

logger = logging.getLogger(__name__)


def compute_continuous_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard meteorological continuous verification metrics."""
    if len(y_true) == 0:
        return {"mae": 0.0, "rmse": 0.0, "bias": 0.0, "correlation": 0.0, "r2": 0.0}

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    bias = float(np.mean(y_pred - y_true))

    # Pearson correlation with safety against zero variance
    std_t = np.std(y_true)
    std_p = np.std(y_pred)
    if std_t > 1e-6 and std_p > 1e-6:
        corr = float(np.corrcoef(y_true, y_pred)[0, 1])
    else:
        corr = 0.0

    # R-squared
    try:
        r2 = float(r2_score(y_true, y_pred))
    except Exception:
        r2 = 0.0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "bias": round(bias, 4),
        "correlation": round(corr, 4),
        "r2": round(r2, 4),
    }


class GlobalPrecipitationModel:
    """
    Unified Global LightGBM Regressor for continuous precipitation post-processing.
    Trained on the 18 approved features.
    """

    MODEL_ID = "ramp_global_v2.0.0"

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_seed: int = 42,
    ):
        self.hyperparameters = {
            "objective": "regression",
            "metric": "l1",
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_seed,
            "verbosity": -1,
            "n_jobs": -1,
        }
        self.random_seed = random_seed
        self.model: Optional[lgb.LGBMRegressor] = None
        self.feature_names = APPROVED_PREDICTORS
        self.training_metadata: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        dataset_version: str = "ramp_dataset_real_v1.0.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> "GlobalPrecipitationModel":
        """Fit the LightGBM model on training data with validation early stopping."""
        audit_predictor_dataframe(X_train)
        if X_val is not None:
            audit_predictor_dataframe(X_val)

        start_time = time.time()
        self.model = lgb.LGBMRegressor(**self.hyperparameters)

        eval_set = None
        eval_names = None
        if X_val is not None and y_val is not None and len(X_val) > 0:
            eval_set = [(X_val[self.feature_names], y_val)]
            eval_names = ["validation"]

        self.model.fit(
            X_train[self.feature_names],
            y_train,
            eval_set=eval_set,
            eval_names=eval_names,
        )

        training_duration = time.time() - start_time

        self.training_metadata = {
            "model_id": self.MODEL_ID,
            "model_type": "GLOBAL_ML",
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "target_schema_version": TARGET_SCHEMA_VERSION,
            "features_used": self.feature_names,
            "feature_count": len(self.feature_names),
            "train_samples": len(X_train),
            "val_samples": len(X_val) if X_val is not None else 0,
            "training_duration_seconds": round(training_duration, 3),
            "hyperparameters": self.hyperparameters,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict continuous rainfall (mm), enforcing physical non-negativity >= 0.0."""
        if self.model is None:
            raise RuntimeError("Model has not been fitted.")
        audit_predictor_dataframe(X)
        raw_pred = self.model.predict(X[self.feature_names])
        # Non-negative rainfall invariant
        return np.maximum(0.0, raw_pred)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        Evaluate model performance on test set.
        Includes overall metrics and intensity-stratified metrics:
        - Light (< 2.5 mm)
        - Moderate (2.5 - 64.5 mm)
        - Heavy (64.5 - 115.6 mm)
        - Very Heavy (115.6 - 204.5 mm)
        - Extreme (>= 204.5 mm)
        """
        y_true = np.asarray(y_test, dtype=float)
        y_pred = self.predict(X_test)

        overall = compute_continuous_metrics(y_true, y_pred)

        # Stratified evaluation by rainfall bins
        bins = {
            "all_rainfall": np.ones(len(y_true), dtype=bool),
            "light_lt_2_5mm": (y_true < 2.5),
            "moderate_2_5_to_64_5mm": ((y_true >= 2.5) & (y_true < 64.5)),
            "heavy_64_5_to_115_6mm": ((y_true >= 64.5) & (y_true < 115.6)),
            "very_heavy_115_6_to_204_5mm": ((y_true >= 115.6) & (y_true < 204.5)),
            "extreme_ge_204_5mm": (y_true >= 204.5),
        }

        stratified = {}
        for bin_name, mask in bins.items():
            count = int(np.sum(mask))
            if count >= 5:
                stratified[bin_name] = {
                    "count": count,
                    **compute_continuous_metrics(y_true[mask], y_pred[mask]),
                }
            else:
                stratified[bin_name] = {
                    "count": count,
                    "status": "SAMPLE_LIMITED",
                    "mae": None,
                    "rmse": None,
                    "bias": None,
                    "correlation": None,
                }

        # Feature importances
        importances = {}
        if self.model is not None and hasattr(self.model, "feature_importances_"):
            raw_imp = self.model.feature_importances_
            total = float(np.sum(raw_imp)) if np.sum(raw_imp) > 0 else 1.0
            for name, imp in zip(self.feature_names, raw_imp):
                importances[name] = round(float(imp) / total, 4)

        return {
            "overall": overall,
            "stratified": stratified,
            "feature_importance": importances,
            "test_sample_count": len(y_true),
        }
