"""
Formal Data Contract Test: Invariant forecast_valid_time = initialization_time + lead_time_hours.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from ml.dataset.join import ForecastObservationJoiner
from ml.dataset.builder import DatasetBuilder


def test_data_contract_valid_time_invariant():
    """
    DATA CONTRACT TEST:
      Given:
        Forecast initialization = T
        Forecast lead = L
      Then:
        forecast_valid_time = T + L
        Observation target must correspond to: forecast_valid_time
        Predictor columns must not leak future observations.
    """
    T = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    L = 24
    expected_valid = T + timedelta(hours=L)

    fc_df = pd.DataFrame([{
        "forecast_initialization_time": T,
        "forecast_valid_time": expected_valid,
        "lead_time_hours": L,
        "latitude": 21.0,
        "longitude": 78.0,
        "raw_nwp_rainfall": 20.0,
        "u850": 8.0,
        "v850": 2.0,
        "provider": "GFS",
        "model": "FV3",
    }])

    obs_df = pd.DataFrame([{
        "target_valid_time": expected_valid,
        "latitude": 21.0,
        "longitude": 78.0,
        "observed_rainfall_mm": 22.5,
        "observation_quality_flag": "VALID",
        "observation_source": "IMD_025",
    }])

    joiner = ForecastObservationJoiner()
    joined = joiner.join(fc_df, obs_df)

    assert len(joined) == 1
    row = joined.iloc[0]

    # Check contract invariants
    assert row["forecast_initialization_time"] == T
    assert row["lead_time_hours"] == L
    assert row["forecast_valid_time"] == expected_valid
    assert row["target_valid_time"] == expected_valid
    assert row["observed_rainfall_mm"] == 22.5


def test_data_contract_violation_raises():
    """If valid_time != init + lead, joiner must reject row."""
    T = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    L = 24
    corrupted_valid = T + timedelta(hours=48)  # wrong!

    fc_corrupt = pd.DataFrame([{
        "forecast_initialization_time": T,
        "forecast_valid_time": corrupted_valid,
        "lead_time_hours": L,
        "latitude": 21.0,
        "longitude": 78.0,
        "raw_nwp_rainfall": 20.0,
    }])

    obs_df = pd.DataFrame([{
        "target_valid_time": corrupted_valid,
        "latitude": 21.0,
        "longitude": 78.0,
        "observed_rainfall_mm": 10.0,
    }])

    joiner = ForecastObservationJoiner()
    with pytest.raises(ValueError, match="Data Contract Violation"):
        joiner.join(fc_corrupt, obs_df)
