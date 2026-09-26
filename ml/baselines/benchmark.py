"""
RAMP Baseline Benchmark Engine
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Executes multi-model comparison across the 4 baselines:
  RAW NWP vs MEAN BIAS vs QUANTILE MAPPING vs GLOBAL ML
Evaluates overall, cross-lead-time, threshold-specific, regime-stratified,
and spatial metrics under the same evaluation period and targets.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.diagnostics.lead_time_stratification import LeadTimeStratifiedEvaluator
from ml.baselines.diagnostics.regime_stratification import RegimeStratifiedEvaluator
from ml.baselines.diagnostics.spatial_evaluation import SpatialEvaluator
from ml.baselines.verification.bootstrap import BootstrapComparator
from ml.baselines.verification.metrics import (
    CANONICAL_THRESHOLDS,
    calculate_all_threshold_metrics,
    calculate_continuous_metrics,
)


class BaselineBenchmarkEngine:
    """
    Unified benchmarking engine evaluating all 4 post-processing systems.
    """

    MODEL_KEYS: List[str] = ["raw_nwp", "mean_bias", "quantile_mapping", "global_ml"]

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", dataset_version: str = "v0.3.0") -> None:
        self.data_mode = data_mode
        self.dataset_version = dataset_version

    def run_benchmark(
        self,
        predictions_df: pd.DataFrame,
        obs_col: str = "observed_rainfall_mm",
    ) -> Dict[str, Any]:
        """
        Executes full benchmark evaluation on a held-out test predictions DataFrame.
        """
        df = predictions_df.copy()
        y_obs = df[obs_col].values
        n_samples = len(df)

        available_models = [m for m in self.MODEL_KEYS if m in df.columns]

        # 1. Overall Continuous Metrics
        overall_metrics: Dict[str, Any] = {}
        for m in available_models:
            y_pred = df[m].values
            overall_metrics[m] = calculate_continuous_metrics(y_pred, y_obs)

        # 2. Categorical / Threshold Metrics
        threshold_metrics: Dict[str, Any] = {}
        for m in available_models:
            y_pred = df[m].values
            threshold_metrics[m] = calculate_all_threshold_metrics(y_pred, y_obs)

        # 3. Cross-Lead-Time Stratification
        lead_time_res = LeadTimeStratifiedEvaluator.evaluate(
            df, model_names=available_models, obs_col=obs_col
        )

        # 4. Regime-Stratified Error Diagnostics (Post-Hoc)
        regime_res = RegimeStratifiedEvaluator().evaluate(
            df, model_names=available_models, obs_col=obs_col
        )

        # 5. Spatial Diagnostics
        spatial_res = SpatialEvaluator.evaluate_grid_points(
            df, model_names=available_models, obs_col=obs_col
        )

        # 6. Statistical Significance / Bootstrap Comparison vs RAW NWP
        bootstrap_comp: Dict[str, Any] = {}
        if "raw_nwp" in available_models:
            comparator = BootstrapComparator(n_bootstraps=300)
            raw_preds = df["raw_nwp"].values
            for m in available_models:
                if m != "raw_nwp":
                    bootstrap_comp[f"{m}_vs_raw_nwp"] = comparator.compare_continuous(
                        df[m].values, raw_preds, y_obs
                    )

        # Assemble Master Benchmark Matrix
        benchmark_matrix: List[Dict[str, Any]] = []
        for m in available_models:
            row: Dict[str, Any] = {
                "model": m,
                "rmse": overall_metrics[m]["rmse"],
                "mae": overall_metrics[m]["mae"],
                "mean_bias": overall_metrics[m]["mean_bias"],
                "pearson_r": overall_metrics[m]["pearson_r"],
                "rain_occurrence_csi": threshold_metrics[m]["rain_occurrence"]["csi"],
                "heavy_rain_csi_64_5": threshold_metrics[m]["heavy_rainfall"]["csi"],
                "heavy_rain_pod_64_5": threshold_metrics[m]["heavy_rainfall"]["pod"],
                "heavy_rain_far_64_5": threshold_metrics[m]["heavy_rainfall"]["far"],
                "heavy_rain_ets_64_5": threshold_metrics[m]["heavy_rainfall"]["ets"],
                "very_heavy_csi_115_6": threshold_metrics[m]["very_heavy_rainfall"]["csi"],
                "extremely_heavy_csi_204_5": threshold_metrics[m]["extremely_heavy_rainfall"]["csi"],
            }
            benchmark_matrix.append(row)

        return {
            "evaluation_timestamp": datetime.now().isoformat(),
            "data_mode": self.data_mode,
            "performance_notice": (
                "SYNTHETIC DEMONSTRATION ONLY — Real training data is not available. "
                "These benchmarks establish relative algorithm ladders under synthetic demonstration conditions."
                if self.data_mode != "REAL"
                else "REAL METEOROLOGICAL OBSERVATIONAL VERIFICATION"
            ),
            "dataset_version": self.dataset_version,
            "test_sample_count": n_samples,
            "benchmark_matrix": benchmark_matrix,
            "overall_metrics": overall_metrics,
            "threshold_metrics": threshold_metrics,
            "lead_time_metrics": lead_time_res["lead_time_diagnostics"],
            "regime_metrics": regime_res["regime_diagnostics"],
            "spatial_metrics": spatial_res,
            "bootstrap_significance": bootstrap_comp,
        }
