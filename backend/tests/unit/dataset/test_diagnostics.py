"""
Unit tests for RainfallDistributionDiagnostics: split separation and class imbalance.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import pandas as pd
import pytest

from ml.dataset.diagnostics import RainfallDistributionDiagnostics


def test_diagnostics_split_separation():
    """Statistics must be calculated separately per split and never pooled into train."""
    diag = RainfallDistributionDiagnostics()

    train_df = pd.DataFrame({
        "forecast_valid_time": [datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)] * 4,
        "latitude": [20.0, 20.0, 21.0, 21.0],
        "longitude": [78.0, 79.0, 78.0, 79.0],
        "observed_rainfall_mm": [5.0, 10.0, 15.0, 20.0],
    })

    test_df = pd.DataFrame({
        "forecast_valid_time": [datetime(2025, 7, 20, 0, 0, tzinfo=timezone.utc)] * 2,
        "latitude": [20.0, 21.0],
        "longitude": [78.0, 78.0],
        "observed_rainfall_mm": [100.0, 250.0],  # Heavy and extreme in test
    })

    stats = diag.compute_all_splits(train_df, pd.DataFrame(), test_df)

    # Train mean: mean(5, 10, 15, 20) = 12.5
    assert stats["TRAIN"].rainfall_mean == 12.5
    assert stats["TRAIN"].rainfall_max == 20.0
    assert stats["TRAIN"].event_counts["heavy_rainfall"] == 0

    # Test mean: mean(100, 250) = 175.0
    assert stats["TEST"].rainfall_mean == 175.0
    assert stats["TEST"].rainfall_max == 250.0
    assert stats["TEST"].event_counts["heavy_rainfall"] == 2
    assert stats["TEST"].event_counts["extremely_heavy_rainfall"] == 1


def test_class_imbalance_metrics():
    """Verify positive count, negative count, and ratio calculation."""
    diag = RainfallDistributionDiagnostics()
    df = pd.DataFrame({
        "latitude": [20.0] * 10,
        "longitude": [78.0] * 10,
        "observed_rainfall_mm": [5.0] * 8 + [70.0, 120.0],  # 2 heavy (>=64.5mm)
    })
    s = diag.compute_split_statistics(df, "TRAIN")
    heavy_imb = s.class_imbalance["heavy_rainfall"]
    assert heavy_imb["positive_count"] == 2
    assert heavy_imb["negative_count"] == 8
    assert heavy_imb["positive_ratio"] == 0.2
