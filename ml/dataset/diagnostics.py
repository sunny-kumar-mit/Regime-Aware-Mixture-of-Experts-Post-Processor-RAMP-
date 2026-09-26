"""
RAMP Rainfall Distribution Diagnostics & Statistical Auditing
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Computes rigorous meteorological diagnostics separately for:
  TRAIN, VALIDATION, and TEST splits.

CRITICAL INVARIANTS:
  - NEVER combine test statistics into training reports (zero contamination).
  - Preserves extreme rainfall events (diagnoses outliers without clipping).
  - Explicitly measures class imbalance (positive count, negative count, positive ratio).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from ml.schemas import SplitStatistics


class RainfallDistributionDiagnostics:
    """
    Computes split-specific rainfall distribution parameters, quantiles,
    and class imbalance metrics.
    """

    def __init__(self, observation_col: str = "observed_rainfall_mm") -> None:
        self.observation_col = observation_col

    def compute_split_statistics(self, df: pd.DataFrame, split_name: str) -> SplitStatistics:
        """
        Computes distribution metrics strictly within the provided split.
        """
        if df.empty or self.observation_col not in df.columns:
            return SplitStatistics(
                split_name=split_name,
                row_count=len(df),
                grid_cells=0,
                time_coverage={},
                rainfall_mean=0.0,
                rainfall_median=0.0,
                rainfall_p90=0.0,
                rainfall_p95=0.0,
                rainfall_p99=0.0,
                rainfall_max=0.0,
                event_counts={},
                class_imbalance={},
                feature_missingness={},
            )

        obs = df[self.observation_col].astype(float)
        total_rows = len(df)

        # Unique grid cells
        grid_cells = len(df.groupby(["latitude", "longitude"])) if "latitude" in df.columns else 0

        # Time coverage
        time_cov = {}
        if "forecast_valid_time" in df.columns:
            t = pd.to_datetime(df["forecast_valid_time"], utc=True)
            time_cov = {"start": t.min().isoformat(), "end": t.max().isoformat()}

        # Distribution quantiles
        mean_val = float(obs.mean())
        med_val = float(obs.median())
        p90 = float(obs.quantile(0.90))
        p95 = float(obs.quantile(0.95))
        p99 = float(obs.quantile(0.99))
        max_val = float(obs.max())

        # Event counts
        occ_cnt = int((obs >= 0.1).sum())
        heavy_cnt = int((obs >= 64.5).sum())
        vheavy_cnt = int((obs >= 115.6).sum())
        ext_cnt = int((obs >= 204.5).sum())

        event_counts = {
            "rainfall_occurrence": occ_cnt,
            "heavy_rainfall": heavy_cnt,
            "very_heavy_rainfall": vheavy_cnt,
            "extremely_heavy_rainfall": ext_cnt,
        }

        # Class imbalance calculation
        class_imbalance = {
            "heavy_rainfall": {
                "positive_count": heavy_cnt,
                "negative_count": total_rows - heavy_cnt,
                "positive_ratio": round(heavy_cnt / total_rows, 5) if total_rows > 0 else 0.0,
            },
            "very_heavy_rainfall": {
                "positive_count": vheavy_cnt,
                "negative_count": total_rows - vheavy_cnt,
                "positive_ratio": round(vheavy_cnt / total_rows, 5) if total_rows > 0 else 0.0,
            },
            "extremely_heavy_rainfall": {
                "positive_count": ext_cnt,
                "negative_count": total_rows - ext_cnt,
                "positive_ratio": round(ext_cnt / total_rows, 5) if total_rows > 0 else 0.0,
            },
        }

        # Feature missingness
        missingness = {
            col: round(float(df[col].isnull().mean()), 4)
            for col in df.columns
            if df[col].isnull().any()
        }

        return SplitStatistics(
            split_name=split_name,
            row_count=total_rows,
            grid_cells=grid_cells,
            time_coverage=time_cov,
            rainfall_mean=round(mean_val, 3),
            rainfall_median=round(med_val, 3),
            rainfall_p90=round(p90, 3),
            rainfall_p95=round(p95, 3),
            rainfall_p99=round(p99, 3),
            rainfall_max=round(max_val, 3),
            event_counts=event_counts,
            class_imbalance=class_imbalance,
            feature_missingness=missingness,
        )

    def compute_all_splits(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Dict[str, SplitStatistics]:
        """Calculates diagnostics separately for each partition."""
        return {
            "TRAIN": self.compute_split_statistics(train_df, "TRAIN"),
            "VALIDATION": self.compute_split_statistics(val_df, "VALIDATION"),
            "TEST": self.compute_split_statistics(test_df, "TEST"),
        }

    def compute_histogram_bins(
        self,
        df: pd.DataFrame,
        bins: Optional[List[float]] = None,
    ) -> Dict[str, int]:
        """Computes rainfall distribution counts across meteorological bins."""
        if df.empty or self.observation_col not in df.columns:
            return {}

        bin_edges = bins or [0.0, 0.1, 2.5, 15.6, 64.5, 115.6, 204.5, 1000.0]
        labels = [
            "<0.1mm (Dry)",
            "0.1-2.5mm (Very Light)",
            "2.5-15.6mm (Light)",
            "15.6-64.5mm (Moderate)",
            "64.5-115.6mm (Heavy)",
            "115.6-204.5mm (Very Heavy)",
            ">=204.5mm (Extremely Heavy)",
        ]

        obs = df[self.observation_col]
        categories = pd.cut(obs, bins=bin_edges, labels=labels, right=False)
        counts = categories.value_counts(sort=False).to_dict()
        return {str(k): int(v) for k, v in counts.items()}

    def export_json(
        self,
        stats: Dict[str, SplitStatistics],
        output_path: Path,
    ) -> Path:
        """Serializes split statistics to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = {k: v.model_dump() for k, v in stats.items()}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
        return output_path
