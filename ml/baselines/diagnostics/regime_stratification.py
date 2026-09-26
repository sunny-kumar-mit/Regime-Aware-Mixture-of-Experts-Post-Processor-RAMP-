"""
RAMP Post-Hoc Regime-Stratified Error Diagnostics
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Evaluates how global, unconditioned baseline models perform under each of the 7
Phase 4 meteorological regimes:
  - ACTIVE_MONSOON
  - BREAK_MONSOON
  - LOW_DEPRESSION
  - COASTAL
  - OROGRAPHIC
  - WESTERN_DISTURBANCE
  - TRANSITION_OTHER

Scientific Rationale:
  Baseline models are strictly GLOBAL (trained across all weather states).
  This diagnostic breakdown exposes regime-conditional errors (e.g. global models
  underpredicting during depressions and overpredicting during breaks), establishing
  the core scientific justification for Phase 6 RAMP Mixture-of-Experts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.verification.metrics import (
    calculate_categorical_metrics_for_threshold,
    calculate_continuous_metrics,
)
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime
from ml.regimes.indicators import RegimeIndicatorEngine
from ml.regimes.weak_labeler import RegimeLabeler


class RegimeStratifiedEvaluator:
    """
    Stratifies baseline predictions by Phase 4 weather regimes to identify conditional failure modes.
    """

    def __init__(self) -> None:
        self.regime_order = [r.value for r in REGIME_ORDER]

    def evaluate(
        self,
        predictions_df: pd.DataFrame,
        model_names: List[str],
        regime_col: str = "regime_label",
        obs_col: str = "observed_rainfall_mm",
    ) -> Dict[str, Any]:
        """
        Calculates verification metrics stratified by weather regime.
        predictions_df must contain:
          - obs_col (ground truth)
          - regime_col (Phase 4 regime assignment)
          - columns for each model in model_names (e.g. 'raw_nwp', 'mean_bias', 'quantile_mapping', 'global_ml')
        """
        df = predictions_df.copy()

        # If regime_col is missing or incomplete, classify using RegimeLabeler
        if regime_col not in df.columns or df[regime_col].isnull().all():
            labeler = RegimeLabeler()
            labeled_df = labeler.generate_weak_labels(df)
            df[regime_col] = labeled_df["regime_label"]

        regime_report: Dict[str, Any] = {}

        for regime_name in self.regime_order:
            subset = df[df[regime_col] == regime_name]
            count = len(subset)

            regime_entry: Dict[str, Any] = {
                "regime": regime_name,
                "sample_count": count,
                "models": {},
            }

            if count > 0:
                y_obs = subset[obs_col].values
                for m_name in model_names:
                    if m_name in subset.columns:
                        y_pred = subset[m_name].values
                        cont = calculate_continuous_metrics(y_pred, y_obs)
                        cat_64 = calculate_categorical_metrics_for_threshold(y_pred, y_obs, threshold=64.5)
                        cat_01 = calculate_categorical_metrics_for_threshold(y_pred, y_obs, threshold=0.1)

                        regime_entry["models"][m_name] = {
                            "rmse": cont["rmse"],
                            "mae": cont["mae"],
                            "mean_bias": cont["mean_bias"],
                            "pearson_r": cont["pearson_r"],
                            "rain_occurrence_csi": cat_01["csi"],
                            "heavy_rain_csi": cat_64["csi"],
                            "heavy_rain_pod": cat_64["pod"],
                            "heavy_rain_far": cat_64["far"],
                        }

            regime_report[regime_name] = regime_entry

        return {
            "regime_diagnostics": regime_report,
            "scientific_rationale": (
                "Evaluated post-hoc on globally-fitted baseline predictions. "
                "Exposes regime-dependent error biases justifying Phase 6 RAMP Mixture-of-Experts."
            ),
        }
