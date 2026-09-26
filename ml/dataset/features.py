"""
RAMP Feature Engineering Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Builds canonical and derived meteorological, spatial, and temporal features.
Enforces strict scientific invariants:
  - Wind speed & direction follow standard meteorological conventions.
  - Cyclic encoding for diurnal and annual cycles.
  - Configurable monsoon seasonal partitioning.
  - Spatial neighborhood features computed strictly on NWP predictors (NEVER targets).
  - No forecast error or observation data in predictor matrix X.
  - Optional geographical features (elevation, coast distance) handled gracefully with honest availability.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class FeatureEngineer:
    """
    Orchestrates feature extraction, transformation, and derived meteorological fields.
    """

    def __init__(
        self,
        monsoon_months: Optional[Dict[str, List[int]]] = None,
        compute_spatial: bool = False,
    ) -> None:
        # Configurable seasonal month definitions (IMD standard by default)
        self.monsoon_months = monsoon_months or {
            "pre_monsoon": [3, 4, 5],
            "monsoon": [6, 7, 8, 9],
            "post_monsoon": [10, 11, 12],
            "winter": [1, 2],
        }
        self.compute_spatial = compute_spatial

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms raw forecast DataFrame by adding derived meteorological,
        temporal, and spatial features.
        """
        out = df.copy()

        # ---------------------------------------------------------------------
        # 1. Temporal & Cyclic Encodings
        # ---------------------------------------------------------------------
        if "forecast_valid_time" in out.columns:
            if not pd.api.types.is_datetime64_any_dtype(out["forecast_valid_time"]):
                out["forecast_valid_time"] = pd.to_datetime(out["forecast_valid_time"], utc=True)

            doy = out["forecast_valid_time"].dt.dayofyear
            out["day_of_year"] = doy.astype(np.int32)
            out["month"] = out["forecast_valid_time"].dt.month.astype(np.int32)

            # Annual cyclic encoding (period = 365.25 days)
            out["day_of_year_sin"] = np.sin(2.0 * np.pi * doy / 365.25).astype(np.float32)
            out["day_of_year_cos"] = np.cos(2.0 * np.pi * doy / 365.25).astype(np.float32)

            # Diurnal cyclic encoding (period = 24 hours)
            valid_hour = out["forecast_valid_time"].dt.hour
            out["valid_hour"] = valid_hour.astype(np.int32)
            out["valid_hour_sin"] = np.sin(2.0 * np.pi * valid_hour / 24.0).astype(np.float32)
            out["valid_hour_cos"] = np.cos(2.0 * np.pi * valid_hour / 24.0).astype(np.float32)

        if "forecast_initialization_time" in out.columns:
            if not pd.api.types.is_datetime64_any_dtype(out["forecast_initialization_time"]):
                out["forecast_initialization_time"] = pd.to_datetime(out["forecast_initialization_time"], utc=True)
            out["initialization_hour"] = out["forecast_initialization_time"].dt.hour.astype(np.int32)

        # ---------------------------------------------------------------------
        # 2. Configurable Monsoon Seasonal Flags
        # ---------------------------------------------------------------------
        if "month" in out.columns:
            m = out["month"]
            out["pre_monsoon"] = m.isin(self.monsoon_months.get("pre_monsoon", [3, 4, 5])).astype(np.int32)
            out["monsoon"] = m.isin(self.monsoon_months.get("monsoon", [6, 7, 8, 9])).astype(np.int32)
            out["post_monsoon"] = m.isin(self.monsoon_months.get("post_monsoon", [10, 11, 12])).astype(np.int32)
            out["winter"] = m.isin(self.monsoon_months.get("winter", [1, 2])).astype(np.int32)

        # ---------------------------------------------------------------------
        # 3. Derived Meteorological Features: Wind Speed & Direction
        # ---------------------------------------------------------------------
        if "u850" in out.columns and "v850" in out.columns:
            u = out["u850"].astype(float)
            v = out["v850"].astype(float)

            # Horizontal wind speed magnitude
            out["wind_speed_850"] = np.sqrt(u**2 + v**2).astype(np.float32)

            # Meteorological wind direction: direction FROM which wind blows
            # Standard formula: (270 - atan2(v, u) * 180 / pi) % 360
            # Example: Westerly wind (u>0, v=0) -> (270 - 0) % 360 = 270 deg (from West)
            # Southerly wind (u=0, v>0) -> (270 - 90) % 360 = 180 deg (from South)
            # Northerly wind (u=0, v<0) -> (270 - (-90)) % 360 = 360 % 360 = 0 deg (from North)
            rad = np.arctan2(v, u)
            deg = (270.0 - np.degrees(rad)) % 360.0
            out["wind_direction_850"] = deg.astype(np.float32)

        # ---------------------------------------------------------------------
        # 4. Pressure Anomaly (if MSLP present)
        # ---------------------------------------------------------------------
        if "mslp" in out.columns:
            # Regional anomaly: difference from mean over current valid time
            if "forecast_valid_time" in out.columns:
                mslp_means = out.groupby("forecast_valid_time")["mslp"].transform("mean")
                out["mslp_anomaly"] = (out["mslp"] - mslp_means).astype(np.float32)
            else:
                out["mslp_anomaly"] = (out["mslp"] - out["mslp"].mean()).astype(np.float32)

        # ---------------------------------------------------------------------
        # 5. Spatial Neighborhood Features (from NWP predictor only)
        # ---------------------------------------------------------------------
        if self.compute_spatial and "raw_nwp_rainfall" in out.columns and "latitude" in out.columns and "longitude" in out.columns:
            out = self._compute_spatial_features(out)

        # ---------------------------------------------------------------------
        # 6. Geographical Auxiliaries (preserve None if not available)
        # ---------------------------------------------------------------------
        if "elevation" not in out.columns:
            out["elevation"] = None
        if "distance_to_coast" not in out.columns:
            out["distance_to_coast"] = None

        return out

    def _compute_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes 3x3 local neighborhood statistics for raw NWP rainfall forecast.
        Computed STRICTLY on predictor data, never using observation arrays.
        """
        out = df.copy()
        out["rainfall_mean_3x3"] = np.nan
        out["rainfall_max_3x3"] = np.nan
        out["rainfall_std_3x3"] = np.nan

        # Group by initialization time and lead time to isolate a single 2D NWP grid slice
        group_cols = []
        if "forecast_initialization_time" in out.columns and "lead_time_hours" in out.columns:
            group_cols = ["forecast_initialization_time", "lead_time_hours"]
        elif "forecast_valid_time" in out.columns:
            group_cols = ["forecast_valid_time"]
        else:
            return out

        for _, group in out.groupby(group_cols):
            # Pivot into a 2D spatial grid (aggregate by mean if duplicates still exist)
            pivoted = group.pivot_table(index="latitude", columns="longitude", values="raw_nwp_rainfall", aggfunc="mean")
            if pivoted.shape[0] < 3 or pivoted.shape[1] < 3:
                # Fill with raw value if grid slice too small for 3x3
                for idx in group.index:
                    raw_val = out.loc[idx, "raw_nwp_rainfall"]
                    out.loc[idx, "rainfall_mean_3x3"] = raw_val
                    out.loc[idx, "rainfall_max_3x3"] = raw_val
                    out.loc[idx, "rainfall_std_3x3"] = 0.0
                continue

            # Compute 3x3 moving window mean, max, std
            rolled_mean = pivoted.rolling(window=3, center=True, min_periods=1).mean()
            rolled_mean = rolled_mean.T.rolling(window=3, center=True, min_periods=1).mean().T

            rolled_max = pivoted.rolling(window=3, center=True, min_periods=1).max()
            rolled_max = rolled_max.T.rolling(window=3, center=True, min_periods=1).max().T

            rolled_std = pivoted.rolling(window=3, center=True, min_periods=1).std().fillna(0.0)
            rolled_std = rolled_std.T.rolling(window=3, center=True, min_periods=1).mean().T

            # Map back to group indices
            for idx, row in group.iterrows():
                lat, lon = row["latitude"], row["longitude"]
                if lat in pivoted.index and lon in pivoted.columns:
                    out.loc[idx, "rainfall_mean_3x3"] = float(rolled_mean.loc[lat, lon])
                    out.loc[idx, "rainfall_max_3x3"] = float(rolled_max.loc[lat, lon])
                    out.loc[idx, "rainfall_std_3x3"] = float(rolled_std.loc[lat, lon])

        return out
