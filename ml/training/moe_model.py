"""
RAMP Mixture-of-Experts (MoE) Rainfall Post-Processor
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part J & K: RAMP MoE Architecture, Expert Specialization & Diagnostics
Combines soft regime gating with specialized LightGBM regression experts.
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

from ml.regimes.definitions import INT_TO_REGIME, REGIME_ORDER, REGIME_TO_INT, WeatherRegime
from ml.training.config import FEATURE_SCHEMA_VERSION, TARGET_SCHEMA_VERSION
from ml.training.feature_contract import APPROVED_PREDICTORS, audit_predictor_dataframe
from ml.training.global_model import compute_continuous_metrics
from ml.training.regime_model import WeatherRegimeModel

logger = logging.getLogger(__name__)


class RegimeSpecificExpert:
    """Specialized LightGBM regressor for a single weather regime."""

    def __init__(self, regime_name: str, random_seed: int = 42):
        self.regime_name = regime_name
        self.random_seed = random_seed
        self.feature_names = APPROVED_PREDICTORS
        self.model: Optional[lgb.LGBMRegressor] = None

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> "RegimeSpecificExpert":
        # Regime-tailored hyperparameters
        params = {
            "objective": "regression",
            "metric": "l1",
            "n_estimators": 100,
            "learning_rate": 0.05,
            "num_leaves": 24,
            "max_depth": 5,
            "random_state": self.random_seed,
            "verbosity": -1,
            "n_jobs": -1,
        }
        self.model = lgb.LGBMRegressor(**params)
        self.model.fit(X[self.feature_names], y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            # Fallback to raw NWP if expert is not fitted
            raw_col = X["precip_nwp_raw"] if "precip_nwp_raw" in X.columns else np.zeros(len(X))
            return np.maximum(0.0, np.asarray(raw_col, dtype=float))
        raw_pred = self.model.predict(X[self.feature_names])
        return np.maximum(0.0, raw_pred)


class RAMP_MoE_Model:
    """
    Production RAMP Mixture-of-Experts model.
    Combines WeatherRegimeModel (gating network) with 7 RegimeSpecificExperts.
    """

    MODEL_ID = "ramp_moe_v2.0.0"

    def __init__(
        self,
        temperature: float = 1.0,
        random_seed: int = 42,
    ):
        self.temperature = max(0.1, temperature)
        self.random_seed = random_seed
        self.gating_network: Optional[WeatherRegimeModel] = None
        self.experts: Dict[str, RegimeSpecificExpert] = {
            r.value: RegimeSpecificExpert(r.value, random_seed=random_seed + i)
            for i, r in enumerate(REGIME_ORDER)
        }
        self.training_metadata: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        regimes_train: pd.Series | np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series | np.ndarray] = None,
        regimes_val: Optional[pd.Series | np.ndarray] = None,
        dataset_version: str = "ramp_dataset_real_v1.0.0",
        data_mode: str = "SYNTHETIC_DEMO",
    ) -> "RAMP_MoE_Model":
        """
        Fit the gating classifier and all 7 specialized regime experts.
        """
        audit_predictor_dataframe(X_train)
        start_time = time.time()

        # 1. Fit Gating Network
        self.gating_network = WeatherRegimeModel(random_seed=self.random_seed)
        self.gating_network.fit(
            X_train,
            regimes_train,
            X_val=X_val,
            y_val=regimes_val,
            dataset_version=dataset_version,
            data_mode=data_mode,
        )

        # 2. Fit Each Regime-Specific Expert on its partitioned subset (with fallback if sample-limited)
        y_train_arr = np.asarray(y_train, dtype=float)
        regimes_arr = np.asarray(regimes_train)
        # Convert to string labels
        if regimes_arr.dtype.kind not in ("U", "O"):
            regimes_str = np.array([INT_TO_REGIME.get(int(idx), "TRANSITION_OTHER") for idx in regimes_arr])
        else:
            regimes_str = regimes_arr.astype(str)

        expert_stats = {}
        for regime in REGIME_ORDER:
            r_name = regime.value
            mask = (regimes_str == r_name)
            subset_count = int(np.sum(mask))

            if subset_count >= 15:
                self.experts[r_name].fit(X_train[mask], y_train_arr[mask])
                status = "SPECIALIZED_FIT"
            else:
                # If too few samples, fit on global set to ensure robustness
                self.experts[r_name].fit(X_train, y_train_arr)
                status = "FALLBACK_GLOBAL_FIT"

            expert_stats[r_name] = {
                "training_samples": subset_count,
                "fit_strategy": status,
            }

        duration = time.time() - start_time

        self.training_metadata = {
            "model_id": self.MODEL_ID,
            "model_type": "REGIME_AWARE_MOE",
            "dataset_version": dataset_version,
            "data_mode": data_mode,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "target_schema_version": TARGET_SCHEMA_VERSION,
            "number_of_experts": len(self.experts),
            "expert_regimes": [r.value for r in REGIME_ORDER],
            "gating_temperature": self.temperature,
            "expert_fit_stats": expert_stats,
            "training_duration_seconds": round(duration, 3),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Soft-gated prediction:
        RAMP(x) = sum_k p_k(x) * Expert_k(x)
        """
        if self.gating_network is None:
            raise RuntimeError("Gating network not trained.")

        audit_predictor_dataframe(X)

        # 1. Gate probabilities p_k(x)
        raw_gates = self.gating_network.predict_proba(X)
        if self.temperature != 1.0:
            # Temperature scaling on logits
            log_gates = np.log(np.maximum(1e-7, raw_gates)) / self.temperature
            gates = np.exp(log_gates - np.max(log_gates, axis=1, keepdims=True))
            gates /= np.sum(gates, axis=1, keepdims=True)
        else:
            gates = raw_gates

        # 2. Expert predictions
        N = len(X)
        expert_preds = np.zeros((N, len(REGIME_ORDER)), dtype=float)
        for idx, regime in enumerate(REGIME_ORDER):
            expert_preds[:, idx] = self.experts[regime.value].predict(X)

        # 3. Convex combination
        moe_pred = np.sum(gates * expert_preds, axis=1)

        # Invariant: physical non-negativity
        return np.maximum(0.0, moe_pred)

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series | np.ndarray,
        regimes_test: Optional[pd.Series | np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive MoE evaluation:
        - Continuous performance
        - Gating distributions and expert usage frequency
        - Regime-conditioned performance
        """
        y_true = np.asarray(y_test, dtype=float)
        y_pred = self.predict(X_test)
        overall = compute_continuous_metrics(y_true, y_pred)

        # Gating distribution & usage
        gates = self.gating_network.predict_proba(X_test)  # (N, 7)
        avg_gates = np.mean(gates, axis=0)
        dominant_expert = np.argmax(gates, axis=1)

        usage_freq = {}
        for idx, regime in enumerate(REGIME_ORDER):
            r_name = regime.value
            freq = float(np.mean(dominant_expert == idx))
            usage_freq[r_name] = {
                "average_gate_probability": round(float(avg_gates[idx]), 4),
                "dominant_usage_frequency": round(freq, 4),
            }

        # Regime-stratified performance if regimes provided
        regime_performance = {}
        if regimes_test is not None:
            reg_arr = np.asarray(regimes_test)
            if reg_arr.dtype.kind not in ("U", "O"):
                reg_str = np.array([INT_TO_REGIME.get(int(idx), "TRANSITION_OTHER") for idx in reg_arr])
            else:
                reg_str = reg_arr.astype(str)

            for regime in REGIME_ORDER:
                r_name = regime.value
                mask = (reg_str == r_name)
                c = int(np.sum(mask))
                if c >= 5:
                    regime_performance[r_name] = {
                        "sample_count": c,
                        **compute_continuous_metrics(y_true[mask], y_pred[mask]),
                    }
                else:
                    regime_performance[r_name] = {
                        "sample_count": c,
                        "status": "SAMPLE_LIMITED",
                        "mae": None,
                        "rmse": None,
                        "bias": None,
                        "correlation": None,
                    }

        return {
            "overall": overall,
            "expert_usage": usage_freq,
            "regime_conditioned": regime_performance,
            "test_sample_count": len(y_true),
        }
