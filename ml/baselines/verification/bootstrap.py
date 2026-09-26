"""
RAMP Statistical Significance & Bootstrap Comparison Engine
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Implements paired bootstrap resampling to determine whether differences between
competing forecast systems (e.g. Model A vs Model B) are statistically significant.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ml.baselines.verification.metrics import (
    calculate_categorical_metrics_for_threshold,
    calculate_continuous_metrics,
)


class BootstrapComparator:
    """
    Computes paired bootstrap confidence intervals for error metric differences:
      Delta = Metric(Model A) - Metric(Model B)
    """

    def __init__(self, n_bootstraps: int = 500, confidence_level: float = 0.95, random_seed: int = 42) -> None:
        self.n_bootstraps = n_bootstraps
        self.confidence_level = confidence_level
        self.random_seed = random_seed

    def compare_continuous(
        self,
        preds_a: np.ndarray | List[float],
        preds_b: np.ndarray | List[float],
        observations: np.ndarray | List[float],
    ) -> Dict[str, Any]:
        """
        Calculates paired bootstrap differences for RMSE and MAE:
          Delta_RMSE = RMSE_A - RMSE_B (Negative value indicates Model A is better)
        """
        pa = np.asarray(preds_a, dtype=float)
        pb = np.asarray(preds_b, dtype=float)
        obs = np.asarray(observations, dtype=float)

        n = len(obs)
        if n < 5:
            return {"status": "INSUFFICIENT_SAMPLES", "n": n}

        rng = np.random.default_rng(self.random_seed)

        delta_rmse_list = []
        delta_mae_list = []

        base_a = calculate_continuous_metrics(pa, obs)
        base_b = calculate_continuous_metrics(pb, obs)

        observed_delta_rmse = (base_a["rmse"] or 0.0) - (base_b["rmse"] or 0.0)
        observed_delta_mae = (base_a["mae"] or 0.0) - (base_b["mae"] or 0.0)

        for _ in range(self.n_bootstraps):
            indices = rng.integers(0, n, size=n)
            sample_pa = pa[indices]
            sample_pb = pb[indices]
            sample_obs = obs[indices]

            rmse_a = np.sqrt(np.mean((sample_pa - sample_obs) ** 2))
            rmse_b = np.sqrt(np.mean((sample_pb - sample_obs) ** 2))
            delta_rmse_list.append(rmse_a - rmse_b)

            mae_a = np.mean(np.abs(sample_pa - sample_obs))
            mae_b = np.mean(np.abs(sample_pb - sample_obs))
            delta_mae_list.append(mae_a - mae_b)

        alpha = (1.0 - self.confidence_level) / 2.0
        low_pct = alpha * 100.0
        high_pct = (1.0 - alpha) * 100.0

        ci_rmse = [round(float(np.percentile(delta_rmse_list, low_pct)), 4), round(float(np.percentile(delta_rmse_list, high_pct)), 4)]
        ci_mae = [round(float(np.percentile(delta_mae_list, low_pct)), 4), round(float(np.percentile(delta_mae_list, high_pct)), 4)]

        # Statistically significant if 0 is outside CI
        sig_rmse = bool(ci_rmse[0] > 0 or ci_rmse[1] < 0)
        sig_mae = bool(ci_mae[0] > 0 or ci_mae[1] < 0)

        return {
            "n_bootstraps": self.n_bootstraps,
            "confidence_level": self.confidence_level,
            "observed_delta_rmse": round(float(observed_delta_rmse), 4),
            "ci_delta_rmse": ci_rmse,
            "statistically_significant_rmse": sig_rmse,
            "observed_delta_mae": round(float(observed_delta_mae), 4),
            "ci_delta_mae": ci_mae,
            "statistically_significant_mae": sig_mae,
        }
