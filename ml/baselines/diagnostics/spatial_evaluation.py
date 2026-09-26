"""
RAMP Spatial Grid & Regional Evaluation Engine
SIH26080 | Baseline Rainfall Post-Processing & Benchmarking
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.baselines.verification.metrics import calculate_continuous_metrics


class SpatialEvaluator:
    """
    Computes spatial error fields (RMSE, MAE, Mean Bias) across grid cells and coordinates.
    Prepares gridded statistics for Phase 8 district aggregation.
    """

    @staticmethod
    def evaluate_grid_points(
        predictions_df: pd.DataFrame,
        model_names: List[str],
        lat_col: str = "latitude",
        lon_col: str = "longitude",
        obs_col: str = "observed_rainfall_mm",
    ) -> Dict[str, Any]:
        """
        Calculates per-grid-cell error statistics across unique (latitude, longitude) locations.
        """
        if lat_col not in predictions_df.columns or lon_col not in predictions_df.columns:
            return {"spatial_points": [], "total_points": 0}

        df = predictions_df.copy()
        grouped = df.groupby([lat_col, lon_col])

        spatial_points = []

        for (lat, lon), group in grouped:
            point_data: Dict[str, Any] = {
                "latitude": round(float(lat), 2),
                "longitude": round(float(lon), 2),
                "sample_count": len(group),
                "models": {},
            }

            y_obs = group[obs_col].values
            for m_name in model_names:
                if m_name in group.columns:
                    y_pred = group[m_name].values
                    cont = calculate_continuous_metrics(y_pred, y_obs)
                    point_data["models"][m_name] = {
                        "rmse": cont["rmse"],
                        "mae": cont["mae"],
                        "mean_bias": cont["mean_bias"],
                    }

            spatial_points.append(point_data)

        return {
            "total_points": len(spatial_points),
            "spatial_points": spatial_points,
        }
