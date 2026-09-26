"""
Unit Tests for RAMP Physics-Informed Regime Indicators
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pandas as pd
import pytest

from ml.regimes.definitions import WeatherRegime, regime_registry
from ml.regimes.indicators import RegimeIndicatorEngine


@pytest.fixture
def indicator_engine():
    return RegimeIndicatorEngine()


def test_active_monsoon_indicator(indicator_engine):
    """Active monsoon indicator should be high when Somali jet and monsoon rainfall are strong."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 15.0,
        "u850": 9.5,
        "v850": 3.0,
        "wind_speed_850": 10.0,
        "wind_direction_850": 260.0,
        "mslp": 100400.0,
        "mslp_anomaly": -50.0,
        "temperature": 300.0,
        "relative_humidity": 85.0,
        "precipitable_water": 52.0,
        "cape": 600.0,
        "geopotential_height": 5860.0,
        "latitude": 19.0,
        "longitude": 78.0,
        "monsoon": 1,
        "winter": 0,
        "elevation": 200.0,
        "distance_to_coast": 250.0,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["active_score"].iloc[0] >= 0.75
    assert res["break_score"].iloc[0] <= 0.25


def test_break_monsoon_indicator(indicator_engine):
    """Break monsoon indicator should trigger during monsoon with deficit rainfall and weak westerlies."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 0.2,
        "u850": 2.1,
        "v850": 0.5,
        "wind_speed_850": 2.2,
        "wind_direction_850": 270.0,
        "mslp": 101200.0,
        "mslp_anomaly": 150.0,
        "temperature": 303.0,
        "relative_humidity": 60.0,
        "precipitable_water": 35.0,
        "cape": 300.0,
        "geopotential_height": 5880.0,
        "latitude": 22.0,
        "longitude": 79.0,
        "monsoon": 1,
        "winter": 0,
        "elevation": 150.0,
        "distance_to_coast": 300.0,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["break_score"].iloc[0] >= 0.70
    assert res["active_score"].iloc[0] <= 0.25


def test_low_depression_indicator(indicator_engine):
    """Low/Depression signal when MSLP is deeply negative and winds are high."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 35.0,
        "u850": 12.0,
        "v850": 8.0,
        "wind_speed_850": 14.4,
        "wind_direction_850": 210.0,
        "mslp": 99950.0,
        "mslp_anomaly": -280.0,
        "temperature": 298.0,
        "relative_humidity": 92.0,
        "precipitable_water": 58.0,
        "cape": 1400.0,
        "geopotential_height": 5820.0,
        "latitude": 20.5,
        "longitude": 86.0,
        "monsoon": 1,
        "winter": 0,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["low_depression_score"].iloc[0] >= 0.80


def test_coastal_indicator_with_and_without_explicit_distance(indicator_engine):
    """Coastal score uses distance_to_coast when present, or coordinates when absent."""
    # With explicit distance
    df_with_dist = pd.DataFrame([{
        "raw_nwp_rainfall": 20.0,
        "u850": 8.0,
        "v850": 1.0,
        "wind_speed_850": 8.1,
        "wind_direction_850": 260.0,
        "mslp": 100800.0,
        "relative_humidity": 88.0,
        "precipitable_water": 52.0,
        "latitude": 15.0,
        "longitude": 73.8,
        "monsoon": 1,
        "winter": 0,
        "distance_to_coast": 15.0,
    }])
    res1 = indicator_engine.compute_indicators(df_with_dist)
    assert res1["coastal_score"].iloc[0] >= 0.70

    # Without explicit distance (graceful degradation)
    df_no_dist = pd.DataFrame([{
        "raw_nwp_rainfall": 20.0,
        "u850": 8.0,
        "v850": 1.0,
        "wind_speed_850": 8.1,
        "wind_direction_850": 260.0,
        "mslp": 100800.0,
        "relative_humidity": 88.0,
        "precipitable_water": 52.0,
        "latitude": 15.0,
        "longitude": 73.8,
        "monsoon": 1,
        "winter": 0,
    }])
    res2 = indicator_engine.compute_indicators(df_no_dist)
    assert res2["coastal_score"].iloc[0] >= 0.70
    assert res2["missing_indicator_count"].iloc[0] >= 1


def test_orographic_indicator_graceful_degradation(indicator_engine):
    """Orographic indicator works with DEM elevation, or Western Ghats / NE corridor proxy."""
    # Western Ghats corridor without DEM
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 30.0,
        "u850": 10.0,
        "v850": 2.0,
        "wind_speed_850": 10.2,
        "wind_direction_850": 255.0,
        "relative_humidity": 90.0,
        "latitude": 14.5,
        "longitude": 74.5,
        "monsoon": 1,
        "winter": 0,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["orographic_score"].iloc[0] >= 0.70


def test_western_disturbance_indicator(indicator_engine):
    """Western disturbance indicator triggers in Northwest India during winter with 500 hPa trough."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 8.0,
        "u850": 7.0,
        "v850": 1.0,
        "wind_speed_850": 7.1,
        "wind_direction_850": 280.0,
        "mslp": 101600.0,
        "temperature": 285.0,
        "relative_humidity": 65.0,
        "precipitable_water": 20.0,
        "geopotential_height": 5780.0,
        "latitude": 32.0,
        "longitude": 76.0,
        "monsoon": 0,
        "winter": 1,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["western_disturbance_score"].iloc[0] >= 0.75


def test_transition_other_when_indicators_ambiguous(indicator_engine):
    """When no regime achieves high confidence, transition_score should be elevated."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 1.0,
        "u850": 2.0,
        "v850": 1.0,
        "wind_speed_850": 2.2,
        "wind_direction_850": 180.0,
        "mslp": 101000.0,
        "mslp_anomaly": 0.0,
        "temperature": 298.0,
        "relative_humidity": 55.0,
        "precipitable_water": 30.0,
        "latitude": 23.0,
        "longitude": 78.0,
        "monsoon": 0,
        "winter": 0,
        "distance_to_coast": 500.0,
        "elevation": 100.0,
    }])
    res = indicator_engine.compute_indicators(df)
    assert res["transition_score"].iloc[0] >= 0.50
