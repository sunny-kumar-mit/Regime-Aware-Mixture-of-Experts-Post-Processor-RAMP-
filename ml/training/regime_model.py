"""
RAMP Weather Regime Classification Model
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part I: Weather Regime Model Training & Verification
Trains a multi-class LightGBM classifier outputting regime labels and probability vectors.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml.regimes.definitions import INT_TO_REGIME, REGIME_ORDER, REGIME_TO_INT, WeatherRegime
from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    TARGET_SCHEMA_VERSION,
)
from ml.training.feature_contract import APPROVED_PREDICTORS, audit_predictor_dataframe

logger = logging.getLogger(__name__)


class WeatherRegimeModel:
    """
    Multi-class classifier for assigning synoptic weather regimes and gating probability vectors.
    """

    MODEL_ID = "ramp_regime_v2.0.0"

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        random_seed: int = 42,
    ):
        self.hyperparameters = {
            "objective": "multiclass",
            "num_class": len(REGIME_ORDER),
            "metric": "multi_logloss",
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "max_depth": max_depth,
            "random_state": random_seed,
            "verbosity": -1,
            "n_jobs": -1,
        }
        self.random_seed = random_seed
        self.model: Optional[lgb.LGBMClassifier] = None
        self.feature_names = APPROVED_PREDICTORS
        self.training_metadata: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series | np.ndarray] = None,
        dataset_version: str = "ramp_dataset_real_v1.0.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> "WeatherRegimeModel":
        """
        Fit multi-class regime classifier.
        y_train can be string regime names or integer indices.
        """
        audit_predictor_dataframe(X_train)
        if X_val is not None:
            audit_predictor_dataframe(X_val)

        # Convert regime strings to integers if needed
        y_train_arr = np.asarray(y_train)
        if y_train_arr.dtype.kind in ("U", "O"):
            y_train_int = np.array([REGIME_TO_INT.get(str(r), REGIME_TO_INT["TRANSITION_OTHER"]) for r in y_train_arr])
        else:
            y_train_int = y_train_arr.astype(int)

        eval_set = None
        eval_names = None
        if X_val is not None and y_val is not None and len(X_val) > 0:
            y_val_arr = np.asarray(y_val)
            if y_val_arr.dtype.kind in ("U", "O"):
                y_val_int = np.array([REGIME_TO_INT.get(str(r), REGIME_TO_INT["TRANSITION_OTHER"]) for r in y_val_arr])
            else:
                y_val_int = y_val_arr.astype(int)
            eval_set = [(X_val[self.feature_names], y_val_int)]
            eval_names = ["validation"]

        start_time = time.time()
        self.model = lgb.LGBMClassifier(**self.hyperparameters)
        self.model.fit(
            X_train[self.feature_names],
            y_train_int,
            eval_set=eval_set,
            eval_names=eval_names,
        )
        duration = time.time() - start_time

        self.training_metadata = {
            "model_id": self.MODEL_ID,
            "model_type": "WEATHER_REGIME_CLASSIFIER",
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "regime_classes": [r.value for r in REGIME_ORDER],
            "train_samples": len(X_train),
            "val_samples": len(X_val) if X_val is not None else 0,
            "training_duration_seconds": round(duration, 3),
            "hyperparameters": self.hyperparameters,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return 7-dimensional probability vector for each sample."""
        if self.model is None:
            raise RuntimeError("Model has not been fitted.")
        audit_predictor_dataframe(X)
        proba = self.model.predict_proba(X[self.feature_names])
        # Guarantee it has shape (N, 7) even if some classes were unobserved in train
        if proba.shape[1] < len(REGIME_ORDER):
            full_proba = np.zeros((len(X), len(REGIME_ORDER)))
            full_proba[:, : proba.shape[1]] = proba
            return full_proba
        return proba

    def predict(self, X: pd.DataFrame) -> List[str]:
        """Return most likely weather regime label for each sample."""
        proba = self.predict_proba(X)
        indices = np.argmax(proba, axis=1)
        return [INT_TO_REGIME.get(int(idx), "TRANSITION_OTHER") for idx in indices]

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series | np.ndarray) -> Dict[str, Any]:
        """
        Evaluate classification metrics, per-class support and precision/recall.
        Marks regimes with insufficient sample support as SAMPLE_LIMITED.
        """
        y_test_arr = np.asarray(y_test)
        if y_test_arr.dtype.kind in ("U", "O"):
            y_true_int = np.array([REGIME_TO_INT.get(str(r), REGIME_TO_INT["TRANSITION_OTHER"]) for r in y_test_arr])
        else:
            y_true_int = y_test_arr.astype(int)

        proba = self.predict_proba(X_test)
        y_pred_int = np.argmax(proba, axis=1)

        accuracy = float(accuracy_score(y_true_int, y_pred_int))
        bal_acc = float(balanced_accuracy_score(y_true_int, y_pred_int))
        macro_f1 = float(f1_score(y_true_int, y_pred_int, average="macro", zero_division=0))

        # Per-class metrics
        per_class = {}
        cm = confusion_matrix(y_true_int, y_pred_int, labels=list(range(len(REGIME_ORDER))))

        for idx, regime in enumerate(REGIME_ORDER):
            r_name = regime.value
            support = int(np.sum(y_true_int == idx))
            if support < 10:
                per_class[r_name] = {
                    "support": support,
                    "status": "SAMPLE_LIMITED",
                    "precision": None,
                    "recall": None,
                    "f1": None,
                }
            else:
                prec = float(precision_score(y_true_int == idx, y_pred_int == idx, zero_division=0))
                rec = float(recall_score(y_true_int == idx, y_pred_int == idx, zero_division=0))
                f1 = float(f1_score(y_true_int == idx, y_pred_int == idx, zero_division=0))
                per_class[r_name] = {
                    "support": support,
                    "status": "VALIDATED",
                    "precision": round(prec, 4),
                    "recall": round(rec, 4),
                    "f1": round(f1, 4),
                }

        return {
            "accuracy": round(accuracy, 4),
            "balanced_accuracy": round(bal_acc, 4),
            "macro_f1": round(macro_f1, 4),
            "per_class": per_class,
            "confusion_matrix": cm.tolist(),
            "class_names": [r.value for r in REGIME_ORDER],
            "test_sample_count": len(y_true_int),
        }
