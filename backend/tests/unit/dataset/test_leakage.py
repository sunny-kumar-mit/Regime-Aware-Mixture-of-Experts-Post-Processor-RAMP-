"""
Critical Unit Tests for LeakageGuard: Must FAIL LOUDLY on violations.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from ml.dataset.leakage_guard import DataLeakageError, LeakageGuard


def test_leakage_target_in_features_fails_loudly():
    """Invariant 1: Target variables in predictor features X MUST raise DataLeakageError."""
    guard = LeakageGuard()

    # Features list inadvertently containing observed rainfall target
    bad_features = ["raw_nwp_rainfall", "u850", "observed_rainfall_mm", "lead_time_hours"]

    with pytest.raises(DataLeakageError, match="Target variable 'observed_rainfall_mm' found in predictor feature columns X"):
        guard.audit_features(bad_features)


def test_leakage_forecast_error_in_features_fails_loudly():
    """Invariant 9: Actual forecast error in predictor features X MUST raise DataLeakageError."""
    guard = LeakageGuard()

    bad_features = ["raw_nwp_rainfall", "forecast_error_mm", "u850"]

    with pytest.raises(DataLeakageError, match="Forecast error diagnostic 'forecast_error_mm' found in predictor feature columns X"):
        guard.audit_features(bad_features)


def test_leakage_climatology_on_test_fails_loudly():
    """Invariant 4: Fitting climatology on TEST instead of TRAIN MUST raise DataLeakageError."""
    guard = LeakageGuard()

    with pytest.raises(DataLeakageError, match="Climatology fitted on split 'TEST' instead of required training split 'TRAIN'"):
        guard.audit_climatology(climatology_split="TEST", train_split_name="TRAIN")


def test_leakage_preprocessing_on_test_fails_loudly():
    """Invariants 3, 5, 7: Preprocessing manifest fitted on TEST MUST raise DataLeakageError."""
    guard = LeakageGuard()

    bad_manifest = {
        "fitted_on_split": "TEST",
        "imputation_strategy": "MEDIAN_TRAIN",
    }

    with pytest.raises(DataLeakageError, match="Preprocessing manifest indicates statistics were fitted on 'TEST'"):
        guard.audit_preprocessing_manifest(bad_manifest)


def test_leakage_temporal_misalignment_fails_loudly():
    """Invariant 2: Target valid time not matching forecast valid time MUST raise DataLeakageError."""
    guard = LeakageGuard()

    init_t = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    valid_t = init_t + timedelta(hours=24)
    wrong_t = valid_t + timedelta(hours=12)

    df_bad = pd.DataFrame([{
        "forecast_initialization_time": init_t,
        "forecast_valid_time": valid_t,
        "target_valid_time": wrong_t,
    }])

    with pytest.raises(DataLeakageError, match="Observation target timestamp differs from forecast_valid_time"):
        guard.audit_temporal_alignment(df_bad)


def test_leakage_clean_audit_passes():
    """When no leakage exists, audit passes and generates a report."""
    guard = LeakageGuard()
    guard.audit_features(["raw_nwp_rainfall", "u850", "v850", "lead_time_hours"])
    guard.audit_climatology("TRAIN", train_split_name="TRAIN")
    guard.audit_preprocessing_manifest({"fitted_on_split": "TRAIN"})

    report = guard.generate_report()
    assert report.status == "PASS"
    assert len(report.violations) == 0
    assert report.checks_run >= 3
