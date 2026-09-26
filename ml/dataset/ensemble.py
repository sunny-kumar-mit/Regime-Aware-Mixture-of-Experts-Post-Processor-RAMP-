"""
RAMP Ensemble Aggregation & Statistics Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Processes NWP ensemble forecasts (e.g. GEFS, NEPS):
  1. Preserves individual member-level rows (never immediately collapses them).
  2. Computes ensemble statistics (mean, median, spread/std, min, max) ONLY when
     multiple ensemble members exist.
  3. Supports deterministic forecasts without fabricating fake ensemble spread.
"""

from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd


class EnsembleAggregator:
    """
    Computes ensemble summary metrics while preserving member-level fidelity.
    """

    def __init__(self, rainfall_col: str = "raw_nwp_rainfall") -> None:
        self.rainfall_col = rainfall_col

    def has_multiple_members(self, df: pd.DataFrame) -> bool:
        """Checks if dataset contains more than one unique ensemble member."""
        if "ensemble_member" not in df.columns:
            return False
        unique_members = df["ensemble_member"].dropna().unique()
        return len(unique_members) > 1

    def compute_ensemble_statistics(
        self,
        df: pd.DataFrame,
        group_keys: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Computes ensemble summary features when multiple members are present.
        If only 1 member or deterministic forecast exists, leaves ensemble statistics as None.
        """
        out = df.copy()

        if not self.has_multiple_members(out):
            # Deterministic forecast: do not calculate ensemble spread
            out["ensemble_mean_rainfall"] = out[self.rainfall_col]
            out["ensemble_median_rainfall"] = out[self.rainfall_col]
            out["ensemble_std_rainfall"] = 0.0
            out["ensemble_min_rainfall"] = out[self.rainfall_col]
            out["ensemble_max_rainfall"] = out[self.rainfall_col]
            return out

        keys = group_keys or ["forecast_initialization_time", "lead_time_hours", "latitude", "longitude"]
        present_keys = [k for k in keys if k in out.columns]

        grouped = out.groupby(present_keys)[self.rainfall_col]
        means = grouped.transform("mean").astype(np.float32)
        medians = grouped.transform("median").astype(np.float32)
        stds = grouped.transform("std").fillna(0.0).astype(np.float32)
        mins = grouped.transform("min").astype(np.float32)
        maxs = grouped.transform("max").astype(np.float32)

        out["ensemble_mean_rainfall"] = means
        out["ensemble_median_rainfall"] = medians
        out["ensemble_std_rainfall"] = stds
        out["ensemble_min_rainfall"] = mins
        out["ensemble_max_rainfall"] = maxs

        return out
