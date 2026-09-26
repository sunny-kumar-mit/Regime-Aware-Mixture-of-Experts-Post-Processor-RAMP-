"""
Unit Tests for Probability Calibration Engine
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pytest

from ml.regimes.calibration import RegimeCalibrator


def test_calibration_fit_on_validation_only():
    """Calibration must only fit on VALIDATION partition. Other splits raise ValueError."""
    calibrator = RegimeCalibrator(method="isotonic")

    # Generate synthetic validation predictions
    np.random.seed(42)
    n = 200
    raw_probs = np.random.dirichlet(np.ones(7), size=n)
    labels = np.random.randint(0, 7, size=n)

    # Attempting to fit on TEST split must fail
    with pytest.raises(ValueError, match="Data Leakage Violation"):
        calibrator.fit(raw_probs, labels, split_label="TEST")

    # Attempting to fit on TRAIN split must fail
    with pytest.raises(ValueError, match="Data Leakage Violation"):
        calibrator.fit(raw_probs, labels, split_label="TRAIN")

    # Fitting on VALIDATION must succeed
    calibrator.fit(raw_probs, labels, split_label="VALIDATION")
    assert calibrator.is_fitted
    assert calibrator.fitted_split == "VALIDATION"


def test_calibrated_probabilities_sum_to_one():
    """Calibrated probability vector must strictly sum to 1.0 within 1e-5."""
    calibrator = RegimeCalibrator(method="isotonic")

    np.random.seed(42)
    n_val = 150
    val_probs = np.random.dirichlet(np.ones(7), size=n_val)
    val_labels = np.random.randint(0, 7, size=n_val)
    calibrator.fit(val_probs, val_labels, split_label="VALIDATION")

    # Test calibration on arbitrary uncalibrated inputs
    test_probs = np.array([
        [0.70, 0.10, 0.05, 0.05, 0.05, 0.03, 0.02],
        [0.05, 0.05, 0.80, 0.02, 0.02, 0.03, 0.03],
        [0.14, 0.14, 0.14, 0.14, 0.14, 0.15, 0.15],
    ])

    calibrated = calibrator.calibrate(test_probs)
    assert calibrated.shape == (3, 7)

    for i in range(len(calibrated)):
        row_sum = np.sum(calibrated[i])
        assert np.isclose(row_sum, 1.0, atol=1e-5), f"Row {i} calibrated sum = {row_sum}"


def test_single_sample_calibration_sum_to_one():
    """1D probability vector input must calibrate and sum to 1.0."""
    calibrator = RegimeCalibrator(method="sigmoid")
    np.random.seed(42)
    val_probs = np.random.dirichlet(np.ones(7), size=100)
    val_labels = np.random.randint(0, 7, size=100)
    calibrator.fit(val_probs, val_labels, split_label="VALIDATION")

    p_1d = np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.1])
    cal_1d = calibrator.calibrate(p_1d)
    assert cal_1d.shape == (7,)
    assert np.isclose(np.sum(cal_1d), 1.0, atol=1e-5)
