"""
RAMP Weak-Label Generation & Provenance Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Converts physics-informed indicators into audited weak labels with:
  - Full candidate probability distribution summing to 1.0.
  - Provenance tagging (WEAK_RULE).
  - Explicit quality assessment (HIGH, MEDIUM, LOW, UNAVAILABLE).
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np
import pandas as pd

from ml.regimes.definitions import (
    LabelQuality,
    LabelSource,
    REGIME_ORDER,
    WeatherRegime,
)
from ml.regimes.indicators import RegimeIndicatorEngine


class RegimeLabeler:
    """
    Transforms indicator scores into audited candidate probabilities and weak labels.
    """

    SCORE_COLUMNS: List[str] = [
        "active_score",
        "break_score",
        "low_depression_score",
        "coastal_score",
        "orographic_score",
        "western_disturbance_score",
        "transition_score",
    ]

    def __init__(self, temperature: float = 0.5, indicator_engine: Optional[RegimeIndicatorEngine] = None):
        self.temperature = temperature
        self.indicator_engine = indicator_engine or RegimeIndicatorEngine()

    def generate_weak_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates weak labels and candidate probability distributions.
        Output columns added:
          - p_active, p_break, p_depression, p_coastal, p_orographic, p_western_disturbance, p_transition
          - regime_label
          - regime_label_source
          - regime_label_confidence
          - regime_label_quality
        """
        # Ensure indicators exist
        if not all(col in df.columns for col in self.SCORE_COLUMNS):
            working_df = self.indicator_engine.compute_indicators(df)
        else:
            working_df = df.copy()

        scores_mat = working_df[self.SCORE_COLUMNS].values  # shape (N, 7)

        # Apply temperature-scaled softmax to obtain normalized probabilities
        scaled_scores = scores_mat / max(0.1, self.temperature)
        exp_scores = np.exp(scaled_scores - np.max(scaled_scores, axis=1, keepdims=True))
        probs = exp_scores / np.sum(exp_scores, axis=1, keepdims=True)

        prob_cols = [
            f"p_{r.value.lower()}" for r in REGIME_ORDER
        ]

        for idx, col_name in enumerate(prob_cols):
            working_df[col_name] = probs[:, idx].astype(np.float32)

        # Top regime selection and confidence
        top_indices = np.argmax(probs, axis=1)
        top_confidences = np.max(probs, axis=1)

        regime_labels = [REGIME_ORDER[i].value for i in top_indices]
        working_df["regime_label"] = regime_labels
        working_df["regime_label_source"] = LabelSource.WEAK_RULE.value
        working_df["regime_label_confidence"] = top_confidences.astype(np.float32)

        # Quality tier determination
        missing = working_df["missing_indicator_count"].values if "missing_indicator_count" in working_df.columns else np.zeros(len(df))
        qualities = []
        for conf, miss in zip(top_confidences, missing):
            if conf >= 0.40 and miss <= 1:
                qualities.append(LabelQuality.HIGH.value)
            elif conf >= 0.25:
                qualities.append(LabelQuality.MEDIUM.value)
            else:
                qualities.append(LabelQuality.LOW.value)

        working_df["regime_label_quality"] = qualities

        return working_df
