"""
Extreme Rainfall Multi-Threshold Probability Models
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part L & N: Multi-Threshold LightGBM Probability Classifiers with Calibration & Monotonicity
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
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from ml.training.calibration import ProbabilityCalibrator, compute_ece_mce
from ml.training.config import FEATURE_SCHEMA_VERSION, TARGET_SCHEMA_VERSION
from ml.training.feature_contract import APPROVED_PREDICTORS, audit_predictor_dataframe
from ml.training.monotonicity import MonotonicityVerifier

logger = logging.getLogger(__name__)

THRESHOLDS_CONFIG = [
    {"name": "rain_0p1mm", "threshold_mm": 0.1, "col": "prob_rain_0p1mm"},
    {"name": "heavy_64p5mm", "threshold_mm": 64.5, "col": "prob_heavy_64p5mm"},
    {"name": "very_heavy_115p6mm", "threshold_mm": 115.6, "col": "prob_very_heavy_115p6mm"},
    {"name": "extreme_204p5mm", "threshold_mm": 204.5, "col": "prob_extreme_204p5mm"},
]


class ThresholdBinaryClassifier:
    """LightGBM Binary Classifier + Validation-fitted Calibrator for a specific rainfall threshold."""

    def __init__(
        self,
        name: str,
        threshold_mm: float,
        calibration_method: str = "isotonic",
        random_seed: int = 42,
    ):
        self.name = name
        self.threshold_mm = threshold_mm
        self.calibration_method = calibration_method
        self.random_seed = random_seed
        self.model: Optional[lgb.LGBMClassifier] = None
        self.calibrator = ProbabilityCalibrator(method=calibration_method)
        self.feature_names = APPROVED_PREDICTORS

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train_binary: np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val_binary: Optional[np.ndarray] = None,
    ) -> "ThresholdBinaryClassifier":
        # Handle class imbalance if positive cases are rare
        pos_count = int(np.sum(y_train_binary))
        neg_count = len(y_train_binary) - pos_count
        scale_pos_weight = float(neg_count / max(1, pos_count)) if pos_count > 0 else 1.0
        # Cap scale_pos_weight to avoid extreme instability
        scale_pos_weight = min(20.0, max(1.0, scale_pos_weight))

        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "n_estimators": 100,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 5,
            "scale_pos_weight": scale_pos_weight,
            "random_state": self.random_seed,
            "verbosity": -1,
            "n_jobs": -1,
        }

        self.model = lgb.LGBMClassifier(**params)
        eval_set = None
        if X_val is not None and y_val_binary is not None and len(X_val) > 0:
            eval_set = [(X_val[self.feature_names], y_val_binary)]

        self.model.fit(
            X_train[self.feature_names],
            y_train_binary,
            eval_set=eval_set,
        )

        # Strictly fit calibrator on validation predictions
        if X_val is not None and y_val_binary is not None and len(X_val) > 0:
            raw_val_prob = self.model.predict_proba(X_val[self.feature_names])[:, 1]
            self.calibrator.fit(raw_val_prob, y_val_binary)
        else:
            self.calibrator.fit(np.array([0.0, 1.0]), np.array([0, 1]))

        return self

    def predict_proba(self, X: pd.DataFrame, calibrated: bool = True) -> np.ndarray:
        if self.model is None:
            raise RuntimeError(f"Classifier for threshold {self.threshold_mm} mm not trained.")
        raw_prob = self.model.predict_proba(X[self.feature_names])[:, 1]
        if calibrated:
            return self.calibrator.predict(raw_prob)
        return raw_prob


class ExtremeProbabilityModels:
    """
    Suite of 4 IMD rainfall threshold probability models.
    Enforces calibration, evaluation metrics, and monotonicity.
    """

    MODEL_ID = "ramp_extreme_v2.0.0"

    def __init__(self, calibration_method: str = "isotonic", random_seed: int = 42):
        self.calibration_method = calibration_method
        self.random_seed = random_seed
        self.heads: Dict[str, ThresholdBinaryClassifier] = {
            cfg["name"]: ThresholdBinaryClassifier(
                name=cfg["name"],
                threshold_mm=cfg["threshold_mm"],
                calibration_method=calibration_method,
                random_seed=random_seed + i,
            )
            for i, cfg in enumerate(THRESHOLDS_CONFIG)
        }
        self.training_metadata: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train_continuous: np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val_continuous: Optional[np.ndarray] = None,
        dataset_version: str = "ramp_dataset_real_v1.0.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> "ExtremeProbabilityModels":
        audit_predictor_dataframe(X_train)
        if X_val is not None:
            audit_predictor_dataframe(X_val)

        start_time = time.time()
        head_stats = {}

        for cfg in THRESHOLDS_CONFIG:
            name = cfg["name"]
            thresh = cfg["threshold_mm"]

            # Derive binary targets
            y_tr_bin = (y_train_continuous >= thresh).astype(int)
            y_va_bin = (y_val_continuous >= thresh).astype(int) if y_val_continuous is not None else None

            pos_train = int(np.sum(y_tr_bin))
            self.heads[name].fit(X_train, y_tr_bin, X_val, y_va_bin)

            head_stats[name] = {
                "threshold_mm": thresh,
                "train_positives": pos_train,
                "train_prevalence": round(float(pos_train / len(y_tr_bin)), 5),
                "status": "VALIDATED" if pos_train >= 5 else "SAMPLE_LIMITED",
            }

        duration = time.time() - start_time

        self.training_metadata = {
            "model_id": self.MODEL_ID,
            "model_type": "EXTREME_PROBABILITY_MODELS",
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "target_schema_version": TARGET_SCHEMA_VERSION,
            "thresholds_mm": [cfg["threshold_mm"] for cfg in THRESHOLDS_CONFIG],
            "calibration_method": self.calibration_method,
            "head_stats": head_stats,
            "training_duration_seconds": round(duration, 3),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        return self

    def predict_proba_dict(
        self,
        X: pd.DataFrame,
        calibrated: bool = True,
        enforce_monotonicity: bool = True,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Return dict of probabilities for each threshold, with monotonicity audit."""
        probs = {}
        for cfg in THRESHOLDS_CONFIG:
            probs[cfg["col"]] = self.heads[cfg["name"]].predict_proba(X, calibrated=calibrated)

        if enforce_monotonicity:
            probs, mono_report = MonotonicityVerifier.enforce(probs)
        else:
            mono_report = MonotonicityVerifier.audit(probs)

        return probs, mono_report

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test_continuous: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Evaluate all 4 thresholds.
        Metrics: Brier Score, Brier Skill Score, Log Loss, ROC-AUC, PR-AUC, ECE, MCE.
        Reports SAMPLE_LIMITED honestly if event support is insufficient.
        """
        y_test_arr = np.asarray(y_test_continuous, dtype=float)
        probs_uncal, _ = self.predict_proba_dict(X_test, calibrated=False, enforce_monotonicity=False)
        probs_cal, mono_report = self.predict_proba_dict(X_test, calibrated=True, enforce_monotonicity=True)

        results = {}
        for cfg in THRESHOLDS_CONFIG:
            name = cfg["name"]
            col = cfg["col"]
            thresh = cfg["threshold_mm"]

            y_bin = (y_test_arr >= thresh).astype(int)
            pos_count = int(np.sum(y_bin))
            neg_count = len(y_bin) - pos_count
            prevalence = float(pos_count / len(y_bin)) if len(y_bin) > 0 else 0.0

            if pos_count < 5 or neg_count < 5:
                results[name] = {
                    "threshold_mm": thresh,
                    "event_count": pos_count,
                    "non_event_count": neg_count,
                    "prevalence": round(prevalence, 5),
                    "status": "SAMPLE_LIMITED",
                    "brier_score": None,
                    "brier_skill_score": None,
                    "roc_auc": None,
                    "pr_auc": None,
                    "ece": None,
                    "mce": None,
                }
                continue

            p_uncal = probs_uncal[col]
            p_cal = probs_cal[col]

            # Brier Score & BSS
            bs_uncal = float(brier_score_loss(y_bin, p_uncal))
            bs_cal = float(brier_score_loss(y_bin, p_cal))
            bs_ref = float(prevalence * (1.0 - prevalence))
            bss = float(1.0 - (bs_cal / bs_ref)) if bs_ref > 1e-6 else 0.0

            # ROC-AUC & PR-AUC
            roc_auc = float(roc_auc_score(y_bin, p_cal))
            pr_auc = float(average_precision_score(y_bin, p_cal))

            # Log Loss
            ll = float(log_loss(y_bin, np.clip(p_cal, 1e-6, 1.0 - 1e-6)))

            # ECE & MCE
            ece_uncal, mce_uncal, _ = compute_ece_mce(y_bin, p_uncal)
            ece_cal, mce_cal, rel_bins = compute_ece_mce(y_bin, p_cal)

            results[name] = {
                "threshold_mm": thresh,
                "event_count": pos_count,
                "non_event_count": neg_count,
                "prevalence": round(prevalence, 5),
                "status": "VALIDATED",
                "uncalibrated": {
                    "brier_score": round(bs_uncal, 4),
                    "ece": ece_uncal,
                    "mce": mce_uncal,
                },
                "calibrated": {
                    "brier_score": round(bs_cal, 4),
                    "brier_skill_score": round(bss, 4),
                    "log_loss": round(ll, 4),
                    "roc_auc": round(roc_auc, 4),
                    "pr_auc": round(pr_auc, 4),
                    "ece": ece_cal,
                    "mce": mce_cal,
                    "reliability_bins": rel_bins,
                },
            }

        return {
            "thresholds": results,
            "monotonicity": mono_report,
            "test_sample_count": len(y_test_arr),
        }
