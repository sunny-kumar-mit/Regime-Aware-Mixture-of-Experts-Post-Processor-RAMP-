"""
Unit Tests for Phase 5 Verification Metrics:
- Continuous verification (RMSE, MAE, Mean Bias, Pearson R)
- Categorical verification (POD, FAR, CSI, ETS, FBIAS)
- Threshold calculation (0.1, 64.5, 115.6, 204.5 mm)
- Fractional Skill Score (FSSCalculator)
- Bootstrap Paired Comparison (BootstrapComparator)
SIH26080 | MoES / NCMRWF
"""

import pytest
import numpy as np
from ml.baselines.verification.metrics import (
    calculate_continuous_metrics,
    calculate_contingency_table,
    calculate_pod,
    calculate_far,
    calculate_csi,
    calculate_ets,
    calculate_categorical_metrics_for_threshold,
    calculate_all_threshold_metrics,
    CANONICAL_THRESHOLDS,
)
from ml.baselines.verification.fss import FSSCalculator
from ml.baselines.verification.bootstrap import BootstrapComparator


def test_continuous_metrics_perfect():
    y_true = np.array([0.0, 10.0, 25.0, 70.0, 150.0])
    y_pred = y_true.copy()

    metrics = calculate_continuous_metrics(y_pred, y_true)
    assert metrics["rmse"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["mean_bias"] == 0.0
    assert metrics["pearson_r"] == 1.0


def test_continuous_metrics_known_bias():
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = y_true + 2.0

    metrics = calculate_continuous_metrics(y_pred, y_true)
    assert np.isclose(metrics["rmse"], 2.0)
    assert np.isclose(metrics["mae"], 2.0)
    assert np.isclose(metrics["mean_bias"], 2.0)


def test_contingency_table_and_categorical_metrics():
    # 4 samples:
    # 1: hit (obs >= 64.5, pred >= 64.5)
    # 2: miss (obs >= 64.5, pred < 64.5)
    # 3: false alarm (obs < 64.5, pred >= 64.5)
    # 4: correct negative (obs < 64.5, pred < 64.5)
    y_true = np.array([70.0, 80.0, 10.0, 5.0])
    y_pred = np.array([75.0, 20.0, 90.0, 0.0])

    table = calculate_contingency_table(y_pred, y_true, threshold=64.5)
    assert table["hits"] == 1
    assert table["misses"] == 1
    assert table["false_alarms"] == 1
    assert table["correct_negatives"] == 1
    assert table["total"] == 4

    # Calculate metrics
    pod = calculate_pod(table["hits"], table["misses"])
    far = calculate_far(table["hits"], table["false_alarms"])
    csi = calculate_csi(table["hits"], table["misses"], table["false_alarms"])
    ets = calculate_ets(table["hits"], table["misses"], table["false_alarms"], table["correct_negatives"])

    # POD = 1 / (1 + 1) = 0.5
    assert pod == 0.5
    # FAR = 1 / (1 + 1) = 0.5
    assert far == 0.5
    # CSI = 1 / (1 + 1 + 1) = 0.333333
    assert np.isclose(csi, 1.0 / 3.0, atol=1e-3)
    # Hits_random = (2 * 2) / 4 = 1.0
    # ETS = (1 - 1) / (1 + 1 + 1 - 1) = 0.0
    assert ets == 0.0


def test_zero_denominator_safe_handling():
    # No events observed or predicted
    y_true = np.array([5.0, 10.0, 15.0])
    y_pred = np.array([4.0, 11.0, 14.0])

    table = calculate_contingency_table(y_pred, y_true, threshold=64.5)
    pod = calculate_pod(table["hits"], table["misses"])
    far = calculate_far(table["hits"], table["false_alarms"])
    csi = calculate_csi(table["hits"], table["misses"], table["false_alarms"])
    ets = calculate_ets(table["hits"], table["misses"], table["false_alarms"], table["correct_negatives"])

    assert pod is None
    assert far is None
    assert csi is None
    # With 0 hits and 0 denom, ETS returns 0.0
    assert ets == 0.0


def test_calculate_all_threshold_metrics():
    y_true = np.array([0.0, 5.0, 70.0, 120.0, 210.0])
    y_pred = np.array([0.0, 6.0, 65.0, 110.0, 220.0])

    report = calculate_all_threshold_metrics(y_pred, y_true)
    for thresh_key in CANONICAL_THRESHOLDS:
        assert thresh_key in report
        assert "csi" in report[thresh_key]
        assert "pod" in report[thresh_key]
        assert "far" in report[thresh_key]


def test_fss_calculator():
    fss_calc = FSSCalculator()
    grid_shape = (20, 20)
    obs_grid = np.zeros(grid_shape)
    pred_grid = np.zeros(grid_shape)

    # Put heavy rain in a 4x4 subgrid
    obs_grid[5:9, 5:9] = 75.0
    pred_grid[5:9, 5:9] = 80.0

    scores = fss_calc.evaluate_scales(pred_grid, obs_grid, threshold=64.5)
    assert "25km" in scores
    assert "50km" in scores
    assert "100km" in scores
    assert "200km" in scores
    # Since forecast matches observed pattern exactly at 64.5mm, FSS should be 1.0
    assert np.isclose(scores["25km"], 1.0)
    assert np.isclose(scores["50km"], 1.0)


def test_bootstrap_comparator():
    np.random.seed(42)
    n = 100
    y_true = np.random.exponential(scale=10.0, size=n)
    raw_nwp = y_true + np.random.normal(2.0, 5.0, size=n)
    improved = y_true + np.random.normal(0.0, 3.0, size=n)

    comp = BootstrapComparator(n_bootstraps=200, confidence_level=0.95, random_seed=42)
    res = comp.compare_continuous(raw_nwp, improved, y_true)

    assert "n_bootstraps" in res
    assert res["n_bootstraps"] == 200
    assert "observed_delta_rmse" in res
    assert "ci_delta_rmse" in res
