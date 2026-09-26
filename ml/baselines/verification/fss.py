"""
RAMP Fractions Skill Score (FSS) Engine
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF

Implements neighborhood-based spatial verification (Roberts and Lean, 2008):
  FSS = 1 - (MSE / MSE_ref)
Supports multiple spatial neighborhood scales (25 km, 50 km, 100 km, 200 km).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.ndimage import uniform_filter


class FSSCalculator:
    """
    Computes Fractions Skill Score (FSS) across spatial neighborhood window sizes.
    """

    # Approximate window radii at 0.25° grid resolution (~25 km per cell)
    NEIGHBORHOOD_SCALES_KM: Dict[str, int] = {
        "25km": 1,   # 1x1 (exact cell)
        "50km": 3,   # 3x3 window
        "100km": 5,  # 5x5 window
        "200km": 9,  # 9x9 window
    }

    @classmethod
    def compute_fss_2d(
        cls,
        forecast_grid: np.ndarray,
        observation_grid: np.ndarray,
        threshold: float,
        window_size: int = 3,
    ) -> float:
        """
        Calculates FSS for a single 2D spatial grid (lat x lon) at given threshold and window size.
        """
        # Binary event fields
        pred_binary = (forecast_grid >= threshold).astype(float)
        obs_binary = (observation_grid >= threshold).astype(float)

        # Neighborhood fraction fields via 2D uniform filter (box average)
        pred_fraction = uniform_filter(pred_binary, size=window_size, mode="constant", cval=0.0)
        obs_fraction = uniform_filter(obs_binary, size=window_size, mode="constant", cval=0.0)

        mse = float(np.mean((pred_fraction - obs_fraction) ** 2))
        mse_ref = float(np.mean(pred_fraction ** 2 + obs_fraction ** 2))

        if mse_ref < 1e-9:
            # If neither forecast nor observation produced the event anywhere in the domain
            return 1.0 if mse < 1e-9 else 0.0

        fss = 1.0 - (mse / mse_ref)
        return float(np.clip(fss, 0.0, 1.0))

    @classmethod
    def evaluate_scales(
        cls,
        forecast_grid: np.ndarray,
        observation_grid: np.ndarray,
        threshold: float = 64.5,
    ) -> Dict[str, float]:
        """
        Evaluates FSS across all canonical neighborhood scales: 25km, 50km, 100km, 200km.
        """
        results = {}
        for scale_name, win_size in cls.NEIGHBORHOOD_SCALES_KM.items():
            score = cls.compute_fss_2d(
                forecast_grid, observation_grid, threshold=threshold, window_size=win_size
            )
            results[scale_name] = round(score, 4)
        return results
