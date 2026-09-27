"""
Inference Feature Construction & Schema Verification
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part F: Enforces the canonical ramp_features_v1.0.0 feature schema (18 predictors).
Rejects any mismatched features or unexpected column orders.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.training.feature_contract import (
    APPROVED_PREDICTORS,
    FEATURE_NAMES,
    FEATURE_SPECS,
    FeatureContractValidator,
    audit_predictor_dataframe,
)

logger = logging.getLogger(__name__)


class FeatureSchemaMismatchError(ValueError):
    """Raised when inference features deviate from ramp_features_v1.0.0."""
    pass


class InferenceFeatureBuilder:
    """
    Constructs and audits the exact 18 canonical predictors required by RAMP models.
    """

    @classmethod
    def audit_features(cls, df: pd.DataFrame) -> None:
        """Strict verification of feature presence, ordering, and leakage absence."""
        audit_predictor_dataframe(df)

        missing = [f for f in APPROVED_PREDICTORS if f not in df.columns]
        if missing:
            raise FeatureSchemaMismatchError(
                f"FEATURE_SCHEMA_MISMATCH: Missing required approved predictors: {missing}"
            )

    @classmethod
    def build_synthetic_grid_features(
        cls,
        grid_points: List[Dict[str, float]],
        lead_time_hours: int,
        seed: int = 42,
    ) -> pd.DataFrame:
        """
        Generates deterministic, physically grounded atmospheric feature matrices
        for demonstration and pipeline testing across Indian grid coordinates.
        """
        np.random.seed(seed + lead_time_hours)
        n = len(grid_points)

        lats = np.array([p["latitude"] for p in grid_points])
        lons = np.array([p["longitude"] for p in grid_points])

        # Realistic meteorological gradients across India
        # Higher rain on Western Ghats (lon ~ 73-76, lat ~ 8-19) and Northeast (lon > 90)
        wg_mask = (lons >= 72.5) & (lons <= 76.5) & (lats >= 8.5) & (lats <= 19.5)
        ne_mask = (lons >= 89.0) & (lats >= 23.0)

        raw_rain = np.random.gamma(shape=1.5, scale=4.0, size=n)
        raw_rain[wg_mask] *= 3.5
        raw_rain[ne_mask] *= 3.0

        # Predictor approximations
        u850 = np.random.normal(loc=12.0, scale=4.0, size=n)  # Strong westerlies
        v850 = np.random.normal(loc=4.0, scale=3.0, size=n)
        wind_speed = np.sqrt(u850**2 + v850**2)
        wind_dir = (np.degrees(np.arctan2(u850, v850)) + 360.0) % 360.0

        mslp = 1005.0 - (lats - 20.0) * 0.4 + np.random.normal(0, 1.5, size=n)
        mslp_anom = mslp - 1008.0

        temp = 298.15 - (lats - 15.0) * 0.5 + np.random.normal(0, 1.0, size=n)
        rh = np.clip(75.0 + (lons - 75.0) * 0.5 + np.random.normal(0, 8.0, size=n), 10.0, 99.0)
        pw = np.clip(45.0 + (lats * -0.5) + np.random.normal(0, 5.0, size=n), 5.0, 80.0)
        cape = np.clip(np.random.exponential(scale=800.0, size=n), 0.0, 4500.0)
        geo_h = 5840.0 - (lats - 20.0) * 5.0 + np.random.normal(0, 15.0, size=n)

        # Elevation proxy
        elev = np.zeros(n)
        elev[wg_mask] = np.random.uniform(400, 1800, size=np.sum(wg_mask))
        elev[lats > 30.0] = np.random.uniform(800, 3500, size=np.sum(lats > 30.0))

        # Calendar features (approx day 200 = monsoon July/August)
        doy = 200.0
        doy_sin = np.sin(2.0 * np.pi * doy / 365.25)
        doy_cos = np.cos(2.0 * np.pi * doy / 365.25)

        zonal_shear = np.random.normal(loc=-18.0, scale=4.0, size=n)  # Easterly jet aloft
        monsoon_trough = np.random.normal(loc=4.5, scale=1.5, size=n)
        meridional_flow = v850 * 0.8
        convective_instab = np.random.normal(loc=12.0, scale=3.0, size=n)

        t850_c = temp - 273.15

        data = {
            "precip_nwp_raw": np.round(raw_rain, 2),
            "u850": np.round(u850, 2),
            "v850": np.round(v850, 2),
            "mslp": np.round(mslp, 1),
            "t850": np.round(t850_c, 2),
            "cape": np.round(cape, 1),
            "wind_speed_850": np.round(wind_speed, 2),
            "wind_dir_850": np.round(wind_dir, 1),
            "lead_time_hours": np.full(n, int(lead_time_hours), dtype=np.int64),
            "latitude": np.round(lats, 2),
            "longitude": np.round(lons, 2),
            "elevation_m": np.round(elev, 1),
            "day_of_year_sin": np.full(n, round(doy_sin, 4)),
            "day_of_year_cos": np.full(n, round(doy_cos, 4)),
            "zonal_shear": np.round(zonal_shear, 2),
            "monsoon_trough_intensity": np.round(monsoon_trough, 2),
            "meridional_flow": np.round(meridional_flow, 2),
            "convective_instability": np.round(convective_instab, 2),
        }

        df = pd.DataFrame(data)
        cls.audit_features(df)
        return df[APPROVED_PREDICTORS]

