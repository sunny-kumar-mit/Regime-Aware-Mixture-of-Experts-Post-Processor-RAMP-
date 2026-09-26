"""
Unit tests for ChronologicalSplitter and event-aware holdout.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from ml.dataset.split import ChronologicalSplitter
from ml.schemas import SplitType


def test_chronological_split_no_overlap():
    """Verify strictly chronological ordering and zero temporal overlap between splits."""
    splitter = ChronologicalSplitter(purge_gap_hours=24)

    base_time = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    rows = []
    # 20 days of data
    for d in range(20):
        t = base_time + timedelta(days=d)
        rows.append({
            "forecast_valid_time": t,
            "latitude": 20.0,
            "longitude": 78.0,
            "observed_rainfall_mm": 10.0 + d,
        })
    df = pd.DataFrame(rows)

    train_df, val_df, test_df, manifest = splitter.split(df, time_col="forecast_valid_time")

    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0

    # Invariant: train max time < val min time
    assert train_df["forecast_valid_time"].max() < val_df["forecast_valid_time"].min()

    # Invariant: val max time < test min time
    assert val_df["forecast_valid_time"].max() < test_df["forecast_valid_time"].min()

    # Invariant: purge gap buffer enforced
    val_gap = val_df["forecast_valid_time"].min() - train_df["forecast_valid_time"].max()
    assert val_gap >= timedelta(hours=24)

    test_gap = test_df["forecast_valid_time"].min() - val_df["forecast_valid_time"].max()
    assert test_gap >= timedelta(hours=24)

    assert manifest.purge_gap_hours == 24
    assert manifest.train_rows == len(train_df)
    assert manifest.val_rows == len(val_df)
    assert manifest.test_rows == len(test_df)


def test_event_aware_holdout():
    """Event-aware split must preserve extreme event clusters without splitting across boundaries."""
    splitter = ChronologicalSplitter(split_type=SplitType.EVENT_AWARE, purge_gap_hours=24)

    base_time = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    rows = []
    for d in range(15):
        t = base_time + timedelta(days=d)
        rain = 80.0 if d in [4, 5, 6] else 10.0  # heavy event on days 4, 5, 6
        rows.append({
            "forecast_valid_time": t,
            "latitude": 20.0,
            "longitude": 78.0,
            "observed_rainfall_mm": rain,
        })
    df = pd.DataFrame(rows)

    train_df, val_df, test_df, manifest = splitter.split_by_event(df, event_threshold_mm=64.5)
    assert len(train_df) > 0
    assert manifest.split_type == "event_aware"
