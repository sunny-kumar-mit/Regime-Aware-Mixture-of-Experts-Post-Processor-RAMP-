"""
Unit tests for FeatureEngineer, wind derivations, cyclic encodings, and spatial features.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.dataset.features import FeatureEngineer


def test_wind_speed_and_direction():
    """Verify standard meteorological wind convention."""
    fe = FeatureEngineer()

    # Case 1: Westerly wind (u=10, v=0) -> blowing FROM the West (270 deg)
    df_west = pd.DataFrame({"u850": [10.0], "v850": [0.0]})
    out_west = fe.transform(df_west)
    assert np.isclose(out_west["wind_speed_850"].iloc[0], 10.0)
    assert np.isclose(out_west["wind_direction_850"].iloc[0], 270.0)

    # Case 2: Northerly wind (u=0, v=-10) -> blowing FROM the North (0 or 360 deg)
    df_north = pd.DataFrame({"u850": [0.0], "v850": [-10.0]})
    out_north = fe.transform(df_north)
    assert np.isclose(out_north["wind_speed_850"].iloc[0], 10.0)
    assert np.isclose(out_north["wind_direction_850"].iloc[0], 0.0) or np.isclose(out_north["wind_direction_850"].iloc[0], 360.0)

    # Case 3: Southerly wind (u=0, v=10) -> blowing FROM the South (180 deg)
    df_south = pd.DataFrame({"u850": [0.0], "v850": [10.0]})
    out_south = fe.transform(df_south)
    assert np.isclose(out_south["wind_direction_850"].iloc[0], 180.0)


def test_cyclic_temporal_encodings():
    """Verify cyclic sine/cosine properties."""
    fe = FeatureEngineer()
    df = pd.DataFrame({
        "forecast_valid_time": [
            datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc),
        ],
    })
    out = fe.transform(df)

    # valid_hour 0 -> sin=0, cos=1
    assert np.isclose(out["valid_hour_sin"].iloc[0], 0.0, atol=1e-5)
    assert np.isclose(out["valid_hour_cos"].iloc[0], 1.0, atol=1e-5)

    # valid_hour 12 -> sin=0, cos=-1
    assert np.isclose(out["valid_hour_sin"].iloc[1], 0.0, atol=1e-5)
    assert np.isclose(out["valid_hour_cos"].iloc[1], -1.0, atol=1e-5)

    # Invariant: sin^2 + cos^2 == 1
    sin_sq = out["day_of_year_sin"] ** 2 + out["day_of_year_cos"] ** 2
    assert np.allclose(sin_sq, 1.0, atol=1e-5)


def test_monsoon_seasonal_flags():
    """Verify seasonal indicators match IMD definitions."""
    fe = FeatureEngineer()
    df = pd.DataFrame({
        "forecast_valid_time": [
            datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc),  # Winter
            datetime(2025, 4, 15, 0, 0, tzinfo=timezone.utc),  # Pre-monsoon
            datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc),  # Monsoon
            datetime(2025, 11, 15, 0, 0, tzinfo=timezone.utc), # Post-monsoon
        ]
    })
    out = fe.transform(df)
    assert out.loc[0, "winter"] == 1 and out.loc[0, "monsoon"] == 0
    assert out.loc[1, "pre_monsoon"] == 1 and out.loc[1, "monsoon"] == 0
    assert out.loc[2, "monsoon"] == 1 and out.loc[2, "winter"] == 0
    assert out.loc[3, "post_monsoon"] == 1 and out.loc[3, "monsoon"] == 0


def test_spatial_neighborhood_computations():
    """Spatial 3x3 stats computed strictly on raw NWP rainfall."""
    fe = FeatureEngineer(compute_spatial=True)

    # 3x3 grid for a single forecast initialization and lead
    lats = [20.0, 20.25, 20.5]
    lons = [78.0, 78.25, 78.5]
    init_t = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)

    rows = []
    val = 1.0
    for lat in lats:
        for lon in lons:
            rows.append({
                "forecast_initialization_time": init_t,
                "forecast_valid_time": init_t,
                "lead_time_hours": 24,
                "latitude": lat,
                "longitude": lon,
                "raw_nwp_rainfall": val,
            })
            val += 1.0

    df = pd.DataFrame(rows)
    out = fe.transform(df)

    assert "rainfall_mean_3x3" in out.columns
    assert "rainfall_max_3x3" in out.columns
    # Center cell is (20.25, 78.25) -> index 4, value 5.0. 3x3 mean of 1..9 is 5.0
    center_row = out[(out["latitude"] == 20.25) & (out["longitude"] == 78.25)].iloc[0]
    assert np.isclose(center_row["rainfall_mean_3x3"], 5.0)
    assert np.isclose(center_row["rainfall_max_3x3"], 9.0)
