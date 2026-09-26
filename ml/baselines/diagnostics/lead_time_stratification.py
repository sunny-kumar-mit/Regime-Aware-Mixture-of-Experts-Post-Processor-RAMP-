"""
RAMP Cross-Lead-Time Benchmark Diagnostics
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.verification.metrics import (
    calculate_categorical_metrics_for_threshold,
    calculate_continuous_metrics,
)


class LeadTimeStratifiedEvaluator:
    """
    Evaluates forecast skill decay across lead times (Day 1..5 / 24h, 48h, 72h, etc.).
    """

    @staticmethod
    def evaluate(
        predictions_df: pd.DataFrame,
        model_names: List[str],
        lead_time_col: str = "lead_time_hours",
        obs_col: str = "observed_rainfall_mm",
    ) -> Dict[str, Any]:
        """
        Calculates verification metrics stratified by lead time.
        """
        if lead_time_col not in predictions_df.columns:
            return {"lead_time_diagnostics": {}, "available_lead_times": []}

        df = predictions_df.copy()
        lead_times = sorted([int(x) for x in df[lead_time_col].dropna().unique()])

        lead_report: Dict[str, Any] = {}

        for lt in lead_times:
            subset = df[df[lead_time_col] == lt]
            day_num = max(1, lt // 24)
            label = f"Day_{day_num}_{lt}h"

            entry: Dict[str, Any] = {
                "lead_time_hours": lt,
                "lead_time_label": label,
                "sample_count": len(subset),
                "models": {},
            }

            if len(subset) > 0:
                y_obs = subset[obs_col].values
                for m_name in model_names:
                    if m_name in subset.columns:
                        y_pred = subset[m_name].values
                        cont = calculate_continuous_metrics(y_pred, y_obs)
                        cat_64 = calculate_categorical_metrics_for_threshold(y_pred, y_obs, threshold=64.5)

                        entry["models"][m_name] = {
                            "rmse": cont["rmse"],
                            "mae": cont["mae"],
                            "mean_bias": cont["mean_bias"],
                            "heavy_csi": cat_64["csi"],
                            "heavy_pod": cat_64["pod"],
                            "heavy_far": cat_64["far"],
                        }

            lead_report[label] = entry

        return {
            "lead_time_diagnostics": lead_report,
            "available_lead_times": lead_times,
        }
