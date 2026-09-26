"""
Unit tests for ForecastObservationJoiner.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from ml.dataset.join import ForecastObservationJoiner
from ml.schemas import QualityPolicy


def test_join_on_valid_time_only():
    """Verify join matches on forecast_valid_time and NEVER on initialization time alone."""
    joiner = ForecastObservationJoiner()

    init_t = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    valid_t = init_t + timedelta(hours=24)

    fc_df = pd.DataFrame([{
        "forecast_initialization_time": init_t,
        "forecast_valid_time": valid_t,
        "lead_time_hours": 24,
        "latitude": 20.0,
        "longitude": 78.0,
        "raw_nwp_rainfall": 15.0,
        "provider": "GFS",
        "model": "FV3",
    }])

    # Observation at valid_t (correct)
    obs_df_correct = pd.DataFrame([{
        "target_valid_time": valid_t,
        "latitude": 20.0,
        "longitude": 78.0,
        "observed_rainfall_mm": 18.0,
        "observation_quality_flag": "VALID",
        "observation_source": "IMD",
    }])

    joined = joiner.join(fc_df, obs_df_correct)
    assert len(joined) == 1
    assert joined.iloc[0]["observed_rainfall_mm"] == 18.0
    assert joined.iloc[0]["lead_time_hours"] == 24

    # Observation at init_t (incorrect: must NOT match)
    obs_df_wrong = pd.DataFrame([{
        "target_valid_time": init_t,
        "latitude": 20.0,
        "longitude": 78.0,
        "observed_rainfall_mm": 18.0,
        "observation_quality_flag": "VALID",
        "observation_source": "IMD",
    }])

    joined_wrong = joiner.join(fc_df, obs_df_wrong)
    assert len(joined_wrong) == 0


def test_quality_policy_filtering():
    """Verify INVALID and MISSING quality flags are excluded by policy."""
    joiner = ForecastObservationJoiner(quality_policy=QualityPolicy.BALANCED)

    init_t = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    valid_t = init_t + timedelta(hours=24)

    fc_df = pd.DataFrame([
        {"forecast_initialization_time": init_t, "forecast_valid_time": valid_t, "lead_time_hours": 24, "latitude": 20.0, "longitude": 78.0, "raw_nwp_rainfall": 10.0, "provider": "GFS", "model": "M"},
        {"forecast_initialization_time": init_t, "forecast_valid_time": valid_t, "lead_time_hours": 24, "latitude": 21.0, "longitude": 78.0, "raw_nwp_rainfall": 10.0, "provider": "GFS", "model": "M"},
        {"forecast_initialization_time": init_t, "forecast_valid_time": valid_t, "lead_time_hours": 24, "latitude": 22.0, "longitude": 78.0, "raw_nwp_rainfall": 10.0, "provider": "GFS", "model": "M"},
    ])

    obs_df = pd.DataFrame([
        {"target_valid_time": valid_t, "latitude": 20.0, "longitude": 78.0, "observed_rainfall_mm": 10.0, "observation_quality_flag": "VALID", "observation_source": "IMD"},
        {"target_valid_time": valid_t, "latitude": 21.0, "longitude": 78.0, "observed_rainfall_mm": -5.0, "observation_quality_flag": "INVALID", "observation_source": "IMD"},
        {"target_valid_time": valid_t, "latitude": 22.0, "longitude": 78.0, "observed_rainfall_mm": 250.0, "observation_quality_flag": "VALID_EXTREME", "observation_source": "IMD"},
    ])

    out = joiner.join(fc_df, obs_df)
    # INVALID is excluded, VALID and VALID_EXTREME are preserved
    assert len(out) == 2
    assert "INVALID" not in out["observation_quality_flag"].values
    assert "VALID_EXTREME" in out["observation_quality_flag"].values
