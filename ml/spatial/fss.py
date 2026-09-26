"""
RAMP Spatial Fractions Skill Score (FSS) Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF

Implements neighborhood-based spatial verification (Roberts and Lean, 2008):
  FSS = 1 - (MSE / MSE_ref)
Evaluates spatial skill across 5km, 25km, 50km, 100km, 200km neighborhood radii.
Operates honestly: returns NOT_AVAILABLE or SAMPLE_LIMITED when observations are missing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter


class FractionsSkillScoreService:
    """
    Computes spatial Fractions Skill Score across spatial scales and rainfall thresholds.
    """

    # Neighborhood scale windows at 0.25° grid (~25 km cell width)
    WINDOW_SCALES = {
        "5km": 1,    # Sub-grid point (1x1 box)
        "25km": 1,   # 1x1 grid cell (~25km)
        "50km": 3,   # 3x3 window (~75km box, radius ~37km)
        "100km": 5,  # 5x5 window (~125km box)
        "200km": 9,  # 9x9 window (~225km box)
    }

    THRESHOLDS = [0.1, 64.5, 115.6, 204.5]

    @classmethod
    def compute_fss_single(
        cls,
        forecast_grid: np.ndarray,
        observation_grid: np.ndarray,
        threshold: float,
        window_size: int = 3,
    ) -> Dict[str, Any]:
        """
        Computes FSS, MSE, and MSE_ref for a 2D spatial grid (lat x lon) at given threshold.
        """
        # Ensure grids are 2D
        if forecast_grid.ndim != 2 or observation_grid.ndim != 2:
            return {
                "fss": 0.0,
                "mse": 0.0,
                "mse_ref": 0.0,
                "forecast_fraction": 0.0,
                "observed_fraction": 0.0,
                "status": "INVALID_GRID_DIMENSIONS",
            }

        # Binary event occurrence
        f_bin = (forecast_grid >= threshold).astype(float)
        o_bin = (observation_grid >= threshold).astype(float)

        # Neighborhood fractions via 2D moving box average
        f_frac = uniform_filter(f_bin, size=window_size, mode="constant", cval=0.0)
        o_frac = uniform_filter(o_bin, size=window_size, mode="constant", cval=0.0)

        mse = float(np.mean((f_frac - o_frac) ** 2))
        mse_ref = float(np.mean(f_frac ** 2 + o_frac ** 2))

        f_mean_frac = float(np.mean(f_bin))
        o_mean_frac = float(np.mean(o_bin))

        if mse_ref < 1e-9:
            # Event did not occur in either forecast or observations
            fss = 1.0 if mse < 1e-9 else 0.0
            status = "NO_EVENTS_IN_DOMAIN"
        else:
            fss = 1.0 - (mse / mse_ref)
            fss = float(np.clip(fss, 0.0, 1.0))
            status = "PASS"

        return {
            "fss": round(fss, 4),
            "mse": round(mse, 6),
            "mse_ref": round(mse_ref, 6),
            "forecast_fraction": round(f_mean_frac, 4),
            "observed_fraction": round(o_mean_frac, 4),
            "sample_count": int(forecast_grid.size),
            "status": status,
        }

    @classmethod
    def evaluate_spatial_fss(
        cls,
        df: pd.DataFrame,
        forecast_col: str = "ramp_pred",
        obs_col: str = "observed_rainfall_mm",
        lat_col: str = "latitude",
        lon_col: str = "longitude",
    ) -> Dict[str, Any]:
        """
        Pivots DataFrame into 2D grid and evaluates FSS across all scales and thresholds.
        """
        if obs_col not in df.columns or df[obs_col].isna().all():
            return {
                "status": "NOT_AVAILABLE",
                "message": "Observations not available for spatial FSS verification.",
                "fss_curves": {},
            }

        valid_df = df.dropna(subset=[forecast_col, obs_col, lat_col, lon_col])
        if len(valid_df) < 9:
            return {
                "status": "SAMPLE_LIMITED",
                "message": f"Insufficient grid samples ({len(valid_df)}) for 2D spatial filtering.",
                "fss_curves": {},
            }

        # Pivot to 2D
        try:
            piv_f = valid_df.pivot_table(index=lat_col, columns=lon_col, values=forecast_col, aggfunc="mean").values
            piv_o = valid_df.pivot_table(index=lat_col, columns=lon_col, values=obs_col, aggfunc="mean").values
            # Fill remaining NaN cells with 0.0 for uniform filter
            piv_f = np.nan_to_num(piv_f, nan=0.0)
            piv_o = np.nan_to_num(piv_o, nan=0.0)
        except Exception as e:
            return {
                "status": "PIVOT_ERROR",
                "message": f"Could not construct 2D spatial grid: {e}",
                "fss_curves": {},
            }

        curves: Dict[str, Any] = {}
        for t in cls.THRESHOLDS:
            t_key = f"{t}mm"
            curves[t_key] = {}
            for scale_name, w_size in cls.WINDOW_SCALES.items():
                res = cls.compute_fss_single(piv_f, piv_o, threshold=t, window_size=w_size)
                curves[t_key][scale_name] = res

        return {
            "status": "PASS",
            "thresholds": cls.THRESHOLDS,
            "scales": list(cls.WINDOW_SCALES.keys()),
            "fss_curves": curves,
        }
