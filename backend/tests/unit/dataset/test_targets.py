"""
Unit tests for TargetBuilder and ClimatologyBaseline.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.dataset.targets import ClimatologyBaseline, TargetBuilder


def test_target_rainfall_thresholds():
    """Verify target binary flags against IMD standards."""
    tb = TargetBuilder(occurrence_threshold_mm=0.1)

    df = pd.DataFrame({
        "target_valid_time": [datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)] * 5,
        "latitude": [20.0] * 5,
        "longitude": [78.0] * 5,
        "observed_rainfall_mm": [0.05, 0.1, 64.5, 115.6, 204.5],
    })

    out = tb.build_targets(df)

    # 0.05 mm is below 0.1mm -> occurrence=0
    assert out.loc[0, "rainfall_occurrence"] == 0
    assert out.loc[0, "heavy_rainfall"] == 0

    # 0.1 mm -> occurrence=1, heavy=0
    assert out.loc[1, "rainfall_occurrence"] == 1
    assert out.loc[1, "heavy_rainfall"] == 0

    # 64.5 mm -> heavy=1
    assert out.loc[2, "rainfall_occurrence"] == 1
    assert out.loc[2, "heavy_rainfall"] == 1
    assert out.loc[2, "very_heavy_rainfall"] == 0

    # 115.6 mm -> very_heavy=1
    assert out.loc[3, "very_heavy_rainfall"] == 1
    assert out.loc[3, "extremely_heavy_rainfall"] == 0

    # 204.5 mm -> extremely_heavy=1
    assert out.loc[4, "extremely_heavy_rainfall"] == 1


def test_extreme_rainfall_preservation():
    """Extreme rainfall (350mm, 420mm) must NOT be clipped or set to NaN."""
    tb = TargetBuilder()
    df = pd.DataFrame({
        "target_valid_time": [datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)] * 2,
        "latitude": [20.0, 21.0],
        "longitude": [78.0, 79.0],
        "observed_rainfall_mm": [350.0, 420.0],
    })
    out = tb.build_targets(df)
    assert out["observed_rainfall_mm"].iloc[0] == 350.0
    assert out["observed_rainfall_mm"].iloc[1] == 420.0
    assert out["extremely_heavy_rainfall"].sum() == 2


def test_climatology_baseline_train_only():
    """Climatology must fit strictly on TRAIN and reject fitting on test."""
    train_df = pd.DataFrame({
        "target_valid_time": [
            datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc),
        ],
        "latitude": [20.0, 20.0],
        "longitude": [78.0, 78.0],
        "observed_rainfall_mm": [10.0, 20.0],
    })

    climo = ClimatologyBaseline()
    climo.fit(train_df, split_label="TRAIN")
    assert climo.is_fitted
    assert climo.fitted_split == "TRAIN"

    # Leakage check: Reject fitting on TEST
    with pytest.raises(ValueError, match="Data Leakage Violation"):
        climo.fit(train_df, split_label="TEST")


def test_regime_labels_initialized_null():
    """Regime labels must remain None in Phase 3."""
    tb = TargetBuilder()
    df = pd.DataFrame({
        "target_valid_time": [datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)],
        "latitude": [20.0],
        "longitude": [78.0],
        "observed_rainfall_mm": [50.0],
    })
    out = tb.build_targets(df)
    assert out["regime_label"].iloc[0] is None
    assert out["regime_label_source"].iloc[0] is None
    assert out["regime_label_confidence"].iloc[0] is None
