"""
Unit Tests: LeakageGuard Phase 6 RAMP Feature Audit
SIH26080 | RAMP Mixture-of-Experts
"""

import pytest

from ml.dataset.leakage_guard import (
    DataLeakageError,
    LeakageGuard,
    TargetLeakageError,
    audit_ramp_features,
)


def test_audit_ramp_features_valid():
    valid_features = [
        "raw_nwp_rainfall",
        "lead_time_hours",
        "u850",
        "v850",
        "mslp",
        "temperature",
        "relative_humidity",
        "cape",
    ]
    # Should complete without error
    audit_ramp_features(valid_features)


def test_audit_ramp_features_rejects_target_variables():
    forbidden_targets = [
        "observed_rainfall_mm",
        "rainfall_occurrence",
        "heavy_rainfall",
        "very_heavy_rainfall",
        "extremely_heavy_rainfall",
        "forecast_error",
        "forecast_error_mm",
        "actual_rainfall",
    ]
    for target_col in forbidden_targets:
        cols = ["raw_nwp_rainfall", "temperature", target_col]
        with pytest.raises((TargetLeakageError, DataLeakageError)):
            audit_ramp_features(cols)


def test_audit_ramp_features_rejects_future_regime_labels():
    forbidden_regimes = [
        "future_regime",
        "observed_regime",
        "target_regime",
        "observed_regime_label",
    ]
    for r_col in forbidden_regimes:
        cols = ["raw_nwp_rainfall", "cape", r_col]
        with pytest.raises(DataLeakageError, match="TARGET REGIME LEAKAGE"):
            audit_ramp_features(cols)


def test_leakage_guard_comprehensive_report():
    guard = LeakageGuard()
    guard.audit_ramp_features(["raw_nwp_rainfall", "u850", "v850"])
    report = guard.generate_report()

    assert report.status == "PASS"
    assert report.checks_run >= 1
    assert len(report.violations) == 0
