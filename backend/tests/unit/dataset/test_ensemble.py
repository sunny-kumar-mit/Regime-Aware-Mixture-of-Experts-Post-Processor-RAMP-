"""
Unit tests for EnsembleAggregator: member preservation and statistics.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.dataset.ensemble import EnsembleAggregator


def test_ensemble_deterministic_forecast_no_fake_spread():
    """For single deterministic member, ensemble spread/std must be 0, not fabricated."""
    agg = EnsembleAggregator()
    df = pd.DataFrame([{
        "forecast_initialization_time": datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc),
        "lead_time_hours": 24,
        "latitude": 20.0,
        "longitude": 78.0,
        "ensemble_member": None,
        "raw_nwp_rainfall": 25.0,
    }])

    assert not agg.has_multiple_members(df)
    out = agg.compute_ensemble_statistics(df)
    assert out["ensemble_mean_rainfall"].iloc[0] == 25.0
    assert out["ensemble_std_rainfall"].iloc[0] == 0.0


def test_ensemble_multi_member_statistics():
    """When multiple members exist, mean, median, spread/std, min, max are computed correctly."""
    agg = EnsembleAggregator()
    init_t = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    members = ["c00", "p01", "p02", "p03"]
    rain_vals = [10.0, 20.0, 30.0, 40.0]

    rows = []
    for m, r in zip(members, rain_vals):
        rows.append({
            "forecast_initialization_time": init_t,
            "lead_time_hours": 24,
            "latitude": 20.0,
            "longitude": 78.0,
            "ensemble_member": m,
            "raw_nwp_rainfall": r,
        })
    df = pd.DataFrame(rows)

    assert agg.has_multiple_members(df)
    out = agg.compute_ensemble_statistics(df)

    # Invariant: Individual members are preserved (4 rows remain)
    assert len(out) == 4
    # Mean of [10, 20, 30, 40] is 25.0
    assert np.isclose(out["ensemble_mean_rainfall"].iloc[0], 25.0)
    # Median is 25.0
    assert np.isclose(out["ensemble_median_rainfall"].iloc[0], 25.0)
    # Min is 10.0, Max is 40.0
    assert np.isclose(out["ensemble_min_rainfall"].iloc[0], 10.0)
    assert np.isclose(out["ensemble_max_rainfall"].iloc[0], 40.0)
    # Spread/std > 0
    assert out["ensemble_std_rainfall"].iloc[0] > 0.0
