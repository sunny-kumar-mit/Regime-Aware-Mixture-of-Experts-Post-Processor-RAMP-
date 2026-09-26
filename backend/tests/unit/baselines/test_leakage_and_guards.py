"""
Unit Tests for Leakage Protection & Invariants in Phase 5 Baselines
SIH26080 | MoES / NCMRWF
"""

import pytest
import numpy as np
import pandas as pd
from ml.dataset.leakage_guard import (
    LeakageGuard,
    DataLeakageError,
    TargetLeakageError,
    audit_baseline_features,
)
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.global_ml import GlobalMLPostProcessor


def test_audit_baseline_features_valid():
    valid_features = [
        "raw_nwp_rainfall",
        "lead_time_hours",
        "u850",
        "v850",
        "mslp",
        "relative_humidity",
        "precipitable_water",
        "cape",
        "latitude",
        "longitude",
    ]
    # Should pass without exception
    audit_baseline_features(valid_features)


def test_audit_baseline_features_rejects_targets():
    target_forbidden = [
        "observed_rainfall_mm",
        "rainfall_occurrence",
        "heavy_rainfall",
        "very_heavy_rainfall",
        "extremely_heavy_rainfall",
    ]
    for bad_feat in target_forbidden:
        with pytest.raises(TargetLeakageError, match="Target variable"):
            audit_baseline_features(["raw_nwp_rainfall", bad_feat])


def test_audit_baseline_features_rejects_regimes():
    regime_forbidden = [
        "regime_label",
        "regime_code",
        "p_active_monsoon",
        "p_break_monsoon",
        "regime_confidence",
        "active_monsoon_score",
    ]
    for bad_regime in regime_forbidden:
        with pytest.raises(DataLeakageError, match="Regime feature"):
            audit_baseline_features(["raw_nwp_rainfall", bad_regime])


def test_leakage_guard_baseline_audit_wrapper():
    guard = LeakageGuard()
    with pytest.raises(TargetLeakageError):
        guard.audit_baseline_features(["raw_nwp_rainfall", "observed_rainfall_mm"])

    with pytest.raises(DataLeakageError):
        guard.audit_baseline_features(["raw_nwp_rainfall", "regime_label"])


def test_test_data_forbidden_in_mean_bias_fitting():
    """
    CRITICAL INVARIANT:
    If test observations are intentionally passed into the training/fitting stage,
    THE FIT MUST FAIL LOUDLY.
    """
    df_test = pd.DataFrame({
        "raw_nwp_rainfall": [10.0, 20.0, 30.0],
        "lead_time_hours": [24, 24, 24],
    })
    y_test = pd.Series([12.0, 18.0, 29.0])
    corrector = MeanBiasCorrector()
    with pytest.raises(DataLeakageError, match="strictly on 'TRAIN'"):
        corrector.fit(df_test, y_test, split_label="TEST")


def test_test_data_forbidden_in_quantile_mapping_fitting():
    """
    CRITICAL INVARIANT:
    Test empirical CDF must never enter quantile mapping calibration.
    """
    df_test = pd.DataFrame({
        "raw_nwp_rainfall": [5.0, 15.0, 25.0],
        "lead_time_hours": [48, 48, 48],
    })
    y_test = pd.Series([6.0, 14.0, 26.0])
    eqm = EmpiricalQuantileMapper()
    with pytest.raises(DataLeakageError, match="strictly on 'TRAIN'"):
        eqm.fit(df_test, y_test, split_label="TEST")


def test_global_ml_rejects_regime_in_features():
    """
    Global ML model must strictly reject regime features during training.
    """
    df_train = pd.DataFrame({
        "raw_nwp_rainfall": [10.0, 20.0],
        "lead_time_hours": [24, 48],
        "p_active_monsoon": [0.8, 0.1],  # FORBIDDEN
    })
    y_train = pd.Series([12.0, 18.0])
    model = GlobalMLPostProcessor(feature_columns=["raw_nwp_rainfall", "p_active_monsoon"])
    with pytest.raises(DataLeakageError, match="Regime feature"):
        model.fit(df_train, y_train, split_label="TRAIN")
