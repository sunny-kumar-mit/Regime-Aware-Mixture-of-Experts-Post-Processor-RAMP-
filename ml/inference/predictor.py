"""
RAMP Mixture-of-Experts Operational Inference Predictor
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part G: Executes continuous precipitation post-processing via soft regime gating.
RAMP(x) = sum_k p_k(x) * Expert_k(x)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.inference.model_resolver import ResolvedModel
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime

logger = logging.getLogger(__name__)


class RAMPPredictor:
    """
    Executes post-processing inference combining:
    1. Raw NWP precipitation
    2. Global ML precipitation model
    3. Weather regime classification & soft gating probabilities
    4. 7 regime-specialized regression experts
    """

    def __init__(
        self,
        moe_model: ResolvedModel,
        global_model: Optional[ResolvedModel] = None,
        regime_model: Optional[ResolvedModel] = None,
    ):
        self.moe = moe_model
        self.global_model = global_model
        self.regime_model = regime_model

    def predict_field(
        self,
        features_df: pd.DataFrame,
    ) -> Dict[str, np.ndarray]:
        """
        Generates full continuous post-processed forecast fields.
        Returns:
          - raw_nwp (mm)
          - global_ml (mm)
          - ramp_moe (mm)
          - correction (mm, RAMP - Raw NWP)
          - dominant_regime (str)
          - regime_probabilities (N, 7)
          - forecast_uncertainty (mm, expert spread)
        """
        raw_nwp = np.maximum(0.0, np.asarray(features_df["precip_nwp_raw"], dtype=float))

        # 1. Global ML Prediction
        if self.global_model and hasattr(self.global_model.model_object, "predict"):
            global_ml = np.maximum(0.0, self.global_model.model_object.predict(features_df))
        else:
            global_ml = raw_nwp

        # 2. RAMP MoE Prediction
        moe_obj = self.moe.model_object
        ramp_moe = moe_obj.predict(features_df)
        ramp_moe = np.maximum(0.0, ramp_moe)  # Invariant: physical non-negativity

        # 3. Gating Probabilities & Regime Classification
        gating_net = getattr(moe_obj, "gating_network", None)
        if gating_net and hasattr(gating_net, "predict_proba"):
            regime_probs = gating_net.predict_proba(features_df)
            regime_labels = gating_net.predict(features_df)
        else:
            # Fallback uniform
            regime_probs = np.full((len(features_df), len(REGIME_ORDER)), 1.0 / len(REGIME_ORDER))
            regime_labels = ["TRANSITION_OTHER"] * len(features_df)

        # 4. Correction field (RAMP - Raw NWP)
        correction = ramp_moe - raw_nwp

        # 5. Model Uncertainty (Convex expert spread)
        n = len(features_df)
        expert_preds = np.zeros((n, len(REGIME_ORDER)), dtype=float)
        for idx, regime in enumerate(REGIME_ORDER):
            if regime.value in moe_obj.experts:
                expert_preds[:, idx] = moe_obj.experts[regime.value].predict(features_df)
            else:
                expert_preds[:, idx] = ramp_moe

        # Weighted standard deviation across experts
        var = np.sum(regime_probs * (expert_preds - ramp_moe[:, None]) ** 2, axis=1)
        uncertainty = np.sqrt(np.maximum(0.0, var))

        return {
            "raw_nwp": np.round(raw_nwp, 2),
            "global_ml": np.round(global_ml, 2),
            "ramp_moe": np.round(ramp_moe, 2),
            "correction": np.round(correction, 2),
            "dominant_regime": np.array(regime_labels),
            "regime_probabilities": np.round(regime_probs, 4),
            "regime_confidence": np.round(np.max(regime_probs, axis=1), 4),
            "uncertainty": np.round(uncertainty, 2),
        }
