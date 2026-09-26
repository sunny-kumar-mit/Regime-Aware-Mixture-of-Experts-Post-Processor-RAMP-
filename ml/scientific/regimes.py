"""
RAMP Regime-Stratified Verification — Phase 10
SIH26080 | MoES / NCMRWF

Evaluates RAMP performance stratified by Phase 4 forecast-time weather regimes.
Uses ONLY forecast-time regimes (never observed/future regimes).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

REGIMES = [
    "ACTIVE_MONSOON",
    "BREAK_MONSOON",
    "LOW_DEPRESSION",
    "COASTAL",
    "OROGRAPHIC",
    "WESTERN_DISTURBANCE",
    "TRANSITION_OTHER",
]

MIN_REGIME_SAMPLES = 10


@dataclass
class RegimeMetrics:
    regime: str
    n_samples: int
    availability_status: str
    rmse: Optional[float] = None
    mae: Optional[float] = None
    bias: Optional[float] = None
    pearson_r: Optional[float] = None
    heavy_csi: Optional[float] = None
    heavy_pod: Optional[float] = None
    heavy_far: Optional[float] = None
    extreme_brier: Optional[float] = None
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "n_samples": self.n_samples,
            "availability_status": self.availability_status,
            "rmse": self.rmse,
            "mae": self.mae,
            "bias": self.bias,
            "pearson_r": self.pearson_r,
            "heavy_csi": self.heavy_csi,
            "heavy_pod": self.heavy_pod,
            "heavy_far": self.heavy_far,
            "extreme_brier": self.extreme_brier,
            "data_mode": self.data_mode,
        }


class RegimeStratifiedVerification:
    """
    Computes regime-stratified verification for RAMP MoE.
    Uses forecast-time regime assignments from Phase 4 only.
    Never uses future observed regimes (leakage prevention).
    """

    REGIME_ERROR_PROFILES = {
        # RMSE offset, MAE offset, Bias offset, Pearson adjustment
        "ACTIVE_MONSOON":      (3.8, 2.1, 0.5, 0.75),
        "BREAK_MONSOON":       (2.4, 1.3, -0.2, 0.80),
        "LOW_DEPRESSION":      (5.2, 3.1, 1.8, 0.65),
        "COASTAL":             (4.1, 2.5, 0.7, 0.72),
        "OROGRAPHIC":          (6.3, 3.8, 2.1, 0.60),
        "WESTERN_DISTURBANCE": (3.2, 2.0, 0.3, 0.78),
        "TRANSITION_OTHER":    (2.9, 1.7, -0.1, 0.82),
    }

    REGIME_SAMPLE_COUNTS = {
        "ACTIVE_MONSOON":      42,
        "BREAK_MONSOON":       25,
        "LOW_DEPRESSION":      18,
        "COASTAL":             30,
        "OROGRAPHIC":          20,
        "WESTERN_DISTURBANCE": 28,
        "TRANSITION_OTHER":    37,
    }

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def compute_regime_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        regime_labels: np.ndarray,
    ) -> Dict[str, RegimeMetrics]:
        """
        Compute per-regime metrics using forecast-time regime labels.
        regime_labels must be forecast-time assignments (not observed).
        """
        results = {}
        for regime in REGIMES:
            mask = regime_labels == regime
            n = int(np.sum(mask))

            if n < MIN_REGIME_SAMPLES:
                status = "SAMPLE_LIMITED" if n > 0 else "NOT_AVAILABLE"
                results[regime] = RegimeMetrics(
                    regime=regime, n_samples=n, availability_status=status,
                    data_mode=self.data_mode
                )
                continue

            yt, yp = y_true[mask], y_pred[mask]
            residuals = yp - yt
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            mae = float(np.mean(np.abs(residuals)))
            bias = float(np.mean(residuals))

            # Pearson r
            pearson_r = None
            if np.std(yt) > 1e-9 and np.std(yp) > 1e-9:
                pearson_r = float(np.corrcoef(yt, yp)[0, 1])

            # Heavy rain threshold metrics (>= 64.5 mm)
            obs_heavy = yt >= 64.5
            fcst_heavy = yp >= 64.5
            n_heavy = int(np.sum(obs_heavy))

            heavy_csi = heavy_pod = heavy_far = None
            if n_heavy >= 3:
                hit = int(np.sum(obs_heavy & fcst_heavy))
                miss = int(np.sum(obs_heavy & ~fcst_heavy))
                fa = int(np.sum(~obs_heavy & fcst_heavy))
                if hit + miss + fa > 0:
                    heavy_csi = hit / (hit + miss + fa)
                if hit + miss > 0:
                    heavy_pod = hit / (hit + miss)
                if hit + fa > 0:
                    heavy_far = fa / (hit + fa)

            # Extreme prob Brier score placeholder
            extreme_brier = None

            results[regime] = RegimeMetrics(
                regime=regime,
                n_samples=n,
                availability_status="AVAILABLE",
                rmse=round(rmse, 4),
                mae=round(mae, 4),
                bias=round(bias, 4),
                pearson_r=round(pearson_r, 4) if pearson_r is not None else None,
                heavy_csi=round(heavy_csi, 4) if heavy_csi is not None else None,
                heavy_pod=round(heavy_pod, 4) if heavy_pod is not None else None,
                heavy_far=round(heavy_far, 4) if heavy_far is not None else None,
                extreme_brier=extreme_brier,
                data_mode=self.data_mode,
            )
        return results

    def compute_synthetic_regime_metrics(self) -> Dict[str, RegimeMetrics]:
        """
        Compute regime metrics from synthetic test partition.
        Results clearly labeled SYNTHETIC_DEMO.
        Profile-based for reproducible demonstration.
        """
        rng = np.random.RandomState(self.random_seed)
        results = {}

        for regime in REGIMES:
            n = self.REGIME_SAMPLE_COUNTS[regime]
            rmse_off, mae_off, bias_off, pearson_adj = self.REGIME_ERROR_PROFILES[regime]

            y_true = np.abs(rng.exponential(8.0, n))
            y_pred = np.maximum(0, y_true + rng.normal(bias_off, rmse_off * 0.8, n))

            metrics = self.compute_regime_metrics(
                y_true, y_pred,
                np.array([regime] * n)
            )
            results[regime] = metrics[regime]

        return results

    def regime_comparison_table(
        self,
        regime_metrics: Dict[str, RegimeMetrics],
    ) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in regime_metrics.values()]
