"""
Extreme Rainfall Probability Inference & Monotonicity Enforcement
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part H: Generates calibrated exceedance probabilities across 4 canonical IMD thresholds:
  >= 0.1 mm, >= 64.5 mm, >= 115.6 mm, >= 204.5 mm
Strictly enforces monotonicity invariant:
  P(>= 204.5) <= P(>= 115.6) <= P(>= 64.5) <= P(>= 0.1)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from ml.inference.model_resolver import ResolvedModel
from ml.training.monotonicity import MonotonicityVerifier

logger = logging.getLogger(__name__)


class ExtremeProbabilityPredictor:
    """
    Inference handler for multi-threshold extreme precipitation probabilities.
    """

    def __init__(self, extreme_model: ResolvedModel):
        self.model = extreme_model

    def predict_probabilities(
        self,
        features_df: pd.DataFrame,
        enforce_monotonicity: bool = True,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Generate calibrated probabilities for all 4 thresholds.
        Returns:
          - probabilities dict {prob_rain, prob_heavy, prob_very_heavy, prob_extreme}
          - monotonicity audit report
        """
        ext_obj = self.model.model_object

        # Predict calibrated probabilities using registered heads
        probs_dict, mono_report = ext_obj.predict_proba_dict(
            features_df,
            calibrated=True,
            enforce_monotonicity=enforce_monotonicity,
        )

        formatted_probs = {
            "prob_rain": np.round(probs_dict["prob_rain_0p1mm"], 4),
            "prob_heavy": np.round(probs_dict["prob_heavy_64p5mm"], 4),
            "prob_very_heavy": np.round(probs_dict["prob_very_heavy_115p6mm"], 4),
            "prob_extreme": np.round(probs_dict["prob_extreme_204p5mm"], 4),
        }

        return formatted_probs, mono_report
