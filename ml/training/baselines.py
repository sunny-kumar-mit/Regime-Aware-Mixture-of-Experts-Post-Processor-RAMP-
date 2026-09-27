"""
RAMP Baseline Models Suite for Production Evaluation
SIH26080 | MoES / NCMRWF

Implements the 6 required objective baseline models (Section Part G):
1. Raw NWP
2. Simple Bias Correction (Additive & Multiplicative)
3. Linear Regression
4. Ridge Regression
5. Random Forest Regressor
6. Global ML Baseline (LightGBM)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb

from ml.training.feature_contract import FEATURE_NAMES


class BaselineSuite:
    """Manages training and prediction for all 6 objective benchmark models."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self.models: Dict[str, Any] = {}
        self.bias_offset: float = 0.0
        self.bias_scale: float = 1.0

    def fit_all(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """Fits all baseline models on the training partition."""
        y_vals = y_train.values

        # 1. Raw NWP Baseline (No fitting needed)

        self.models["raw_nwp"] = "raw_nwp_identity"

        # 2. Simple Bias Correction (Additive offset)
        if "precip_nwp_raw" in X_train.columns:
            nwp_raw = X_train["precip_nwp_raw"].values
            self.bias_offset = float(np.mean(y_vals) - np.mean(nwp_raw))
            self.models["simple_bias_correction"] = {"offset_mm": self.bias_offset}

        # Features for regression baselines
        X_feats = X_train[FEATURE_NAMES].fillna(0.0).values

        # 3. Linear Regression
        lr = LinearRegression()
        lr.fit(X_feats, y_vals)
        self.models["linear_regression"] = lr

        # 4. Ridge Regression
        ridge = Ridge(alpha=1.0, random_state=self.random_seed)
        ridge.fit(X_feats, y_vals)
        self.models["ridge_regression"] = ridge

        # 5. Random Forest Regressor
        rf = RandomForestRegressor(
            n_estimators=50,
            max_depth=8,
            random_state=self.random_seed,
            n_jobs=-1,
        )
        rf.fit(X_feats, y_vals)
        self.models["random_forest"] = rf

        # 6. Global ML Baseline (LightGBM)
        lgb_model = lgb.LGBMRegressor(
            n_estimators=60,
            learning_rate=0.08,
            max_depth=6,
            random_state=self.random_seed,
            verbosity=-1,
        )
        lgb_model.fit(X_feats, np.log1p(y_vals))
        self.models["global_ml"] = lgb_model

    def predict_model(self, model_name: str, X: pd.DataFrame) -> np.ndarray:
        """Generates predictions for a specific baseline model."""
        if model_name == "raw_nwp":
            return np.maximum(0.0, X["precip_nwp_raw"].values)

        if model_name == "simple_bias_correction":
            raw = X["precip_nwp_raw"].values
            return np.maximum(0.0, raw + self.bias_offset)

        X_feats = X[FEATURE_NAMES].fillna(0.0).values

        if model_name in ["linear_regression", "ridge_regression", "random_forest"]:
            preds = self.models[model_name].predict(X_feats)
            return np.maximum(0.0, preds)

        if model_name == "global_ml":
            log_preds = self.models["global_ml"].predict(X_feats)
            return np.maximum(0.0, np.expm1(log_preds))

        raise ValueError(f"Unknown baseline model: {model_name}")

    def predict_all(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Generates predictions for all 6 baseline models."""
        return {
            "raw_nwp": self.predict_model("raw_nwp", X),
            "simple_bias_correction": self.predict_model("simple_bias_correction", X),
            "linear_regression": self.predict_model("linear_regression", X),
            "ridge_regression": self.predict_model("ridge_regression", X),
            "random_forest": self.predict_model("random_forest", X),
            "global_ml": self.predict_model("global_ml", X),
        }

    fit = fit_all

