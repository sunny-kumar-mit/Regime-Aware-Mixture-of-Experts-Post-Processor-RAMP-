"""
RAMP Forecast-Observation Join Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Joins NWP forecasts with ground-truth IMD observations on:
  (latitude, longitude, forecast_valid_time)

CRITICAL INVARIANTS:
  1. Never join using initialization time alone.
  2. forecast_valid_time = initialization_time + lead_time_hours.
  3. Every joined sample contains (forecast_initialization_time, forecast_valid_time, lead_time_hours).
  4. Quality flags are strictly propagated; INVALID and MISSING targets are excluded according to policy.
  5. Extreme rainfall events (e.g. 200-400mm) are strictly preserved (never clipped).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Optional
import numpy as np
import pandas as pd
from ml.schemas import QualityPolicy


class ForecastObservationJoiner:
    """
    Spatio-temporal joiner aligning NWP forecast grids with IMD observations.
    """

    def __init__(
        self,
        spatial_tolerance_deg: float = 0.05,
        temporal_tolerance_hours: float = 1.0,
        quality_policy: QualityPolicy = QualityPolicy.BALANCED,
    ) -> None:
        self.spatial_tolerance_deg = spatial_tolerance_deg
        self.temporal_tolerance_hours = temporal_tolerance_hours
        self.quality_policy = quality_policy

    def join(
        self,
        forecast_df: pd.DataFrame,
        observation_df: pd.DataFrame,
        auxiliary_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Executes verified spatio-temporal inner join on (latitude, longitude, valid_time).
        """
        # Validate forecast schema
        req_fc_cols = ["forecast_initialization_time", "forecast_valid_time", "lead_time_hours", "latitude", "longitude"]
        for c in req_fc_cols:
            if c not in forecast_df.columns:
                raise KeyError(f"Forecast DataFrame missing required column: '{c}'")

        # Validate observation schema
        req_obs_cols = ["target_valid_time", "latitude", "longitude", "observed_rainfall_mm"]
        for c in req_obs_cols:
            if c not in observation_df.columns:
                raise KeyError(f"Observation DataFrame missing required column: '{c}'")

        fc = forecast_df.copy()
        obs = observation_df.copy()

        # Ensure UTC datetimes
        if not pd.api.types.is_datetime64_any_dtype(fc["forecast_valid_time"]):
            fc["forecast_valid_time"] = pd.to_datetime(fc["forecast_valid_time"], utc=True)
        if not pd.api.types.is_datetime64_any_dtype(fc["forecast_initialization_time"]):
            fc["forecast_initialization_time"] = pd.to_datetime(fc["forecast_initialization_time"], utc=True)
        if not pd.api.types.is_datetime64_any_dtype(obs["target_valid_time"]):
            obs["target_valid_time"] = pd.to_datetime(obs["target_valid_time"], utc=True)

        # Coordinate rounding to canonical grid resolution for exact float matching
        fc["lat_key"] = fc["latitude"].round(2)
        fc["lon_key"] = fc["longitude"].round(2)
        obs["lat_key"] = obs["latitude"].round(2)
        obs["lon_key"] = obs["longitude"].round(2)

        # Perform inner join on spatial coordinates and valid time
        joined = pd.merge(
            fc,
            obs,
            left_on=["lat_key", "lon_key", "forecast_valid_time"],
            right_on=["lat_key", "lon_key", "target_valid_time"],
            suffixes=("", "_obs"),
            how="inner",
        )

        # Clean auxiliary merge keys
        joined = joined.drop(columns=["lat_key", "lon_key"])
        if "latitude_obs" in joined.columns:
            joined = joined.drop(columns=["latitude_obs"])
        if "longitude_obs" in joined.columns:
            joined = joined.drop(columns=["longitude_obs"])

        # Merge auxiliary geographic fields (DEM elevation, coast distance) if present
        if auxiliary_df is not None and not auxiliary_df.empty:
            aux = auxiliary_df.copy()
            aux["lat_key"] = aux["latitude"].round(2)
            aux["lon_key"] = aux["longitude"].round(2)
            joined["lat_key"] = joined["latitude"].round(2)
            joined["lon_key"] = joined["longitude"].round(2)
            joined = pd.merge(
                joined,
                aux.drop(columns=["latitude", "longitude"], errors="ignore"),
                on=["lat_key", "lon_key"],
                how="left",
            )
            joined = joined.drop(columns=["lat_key", "lon_key"])

        # Filter by quality policy
        joined = self._apply_quality_policy(joined)

        # Assign deterministic sample_ids
        if joined.empty:
            joined["sample_id"] = pd.Series(dtype=str)
        else:
            joined["sample_id"] = joined.apply(self._generate_sample_id, axis=1)

        # Validate temporal contract invariant on joined rows
        for idx, row in joined.iterrows():
            expected_valid = row["forecast_initialization_time"] + timedelta(hours=int(row["lead_time_hours"]))
            if abs((row["forecast_valid_time"] - expected_valid).total_seconds()) > 60:
                raise ValueError(
                    f"Data Contract Violation at row {idx}: forecast_valid_time {row['forecast_valid_time']} "
                    f"does not match initialization {row['forecast_initialization_time']} + lead {row['lead_time_hours']}h"
                )

        return joined

    def _apply_quality_policy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies data quality filters based on observation_quality_flag.
        Preserves VALID_EXTREME (e.g. 200-400mm) without outlier deletion.
        """
        if "observation_quality_flag" not in df.columns:
            return df

        flags = df["observation_quality_flag"].astype(str)

        # Never include physically INVALID (e.g. negative rainfall) or MISSING targets
        mask = ~flags.isin(["INVALID", "MISSING"])

        if self.quality_policy == QualityPolicy.STRICT:
            mask = mask & flags.isin(["VALID", "VALID_EXTREME"])
        elif self.quality_policy == QualityPolicy.BALANCED:
            # Include VALID, VALID_EXTREME, review SUSPICIOUS
            mask = mask & flags.isin(["VALID", "VALID_EXTREME", "SUSPICIOUS"])
        # PERMISSIVE allows SUSPICIOUS as well

        return df[mask].copy()

    @staticmethod
    def _generate_sample_id(row: pd.Series) -> str:
        """Generates deterministic 16-character SHA-256 sample hash."""
        seed = (
            f"{row.get('provider', 'nwp')}_"
            f"{row.get('model', 'model')}_"
            f"{row.get('ensemble_member', 'c00')}_"
            f"{row['latitude']:.2f}_"
            f"{row['longitude']:.2f}_"
            f"{row['forecast_initialization_time'].isoformat()}_"
            f"{row['lead_time_hours']}"
        )
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
