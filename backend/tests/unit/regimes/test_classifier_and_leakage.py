"""
Unit Tests for Regime Classifiers and Leakage Prevention
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pandas as pd
import pytest

from ml.dataset.leakage_guard import DataLeakageError
from ml.regimes.classifier import (
    LightGBMRegimeClassifier,
    RandomForestRegimeClassifier,
    RuleBasedBaselineClassifier,
)
from ml.regimes.definitions import REGIME_ORDER


@pytest.fixture
def synthetic_training_data():
    """Generates synthetic predictor feature set and class labels."""
    np.random.seed(42)
    n = 100
    features = {
        "raw_nwp_rainfall": np.random.exponential(10.0, size=n),
        "u850": np.random.normal(6.0, 3.0, size=n),
        "v850": np.random.normal(2.0, 2.0, size=n),
        "wind_speed_850": np.random.uniform(2.0, 15.0, size=n),
        "wind_direction_850": np.random.uniform(180.0, 300.0, size=n),
        "mslp": np.random.normal(100500.0, 500.0, size=n),
        "mslp_anomaly": np.random.normal(0.0, 150.0, size=n),
        "temperature": np.random.normal(300.0, 3.0, size=n),
        "relative_humidity": np.random.uniform(50.0, 95.0, size=n),
        "precipitable_water": np.random.uniform(30.0, 60.0, size=n),
        "cape": np.random.uniform(200.0, 2000.0, size=n),
        "geopotential_height": np.random.normal(5850.0, 40.0, size=n),
        "latitude": np.random.uniform(8.0, 35.0, size=n),
        "longitude": np.random.uniform(68.0, 95.0, size=n),
        "elevation": np.random.uniform(0.0, 1500.0, size=n),
        "distance_to_coast": np.random.uniform(5.0, 800.0, size=n),
        "monsoon": np.random.choice([0, 1], size=n),
        "winter": np.random.choice([0, 1], size=n),
    }
    df = pd.DataFrame(features)
    y = np.random.randint(0, 7, size=n)
    return df, y


def test_rule_based_baseline_predictions(synthetic_training_data):
    """Rule-based baseline outputs 7-class probability distribution summing to 1.0."""
    X, _ = synthetic_training_data
    baseline = RuleBasedBaselineClassifier()
    baseline.fit(X)

    probs = baseline.predict_proba(X)
    assert probs.shape == (len(X), 7)
    sums = np.sum(probs, axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)

    preds = baseline.predict(X)
    assert len(preds) == len(X)
    assert set(preds).issubset(set(range(7)))


def test_random_forest_classifier(synthetic_training_data):
    """Random Forest classifier fits and outputs normalized 7-class probabilities."""
    X, y = synthetic_training_data
    rf = RandomForestRegimeClassifier(n_estimators=20, max_depth=5, random_state=42)
    rf.fit(X, y)

    assert rf.is_fitted
    probs = rf.predict_proba(X)
    assert probs.shape == (len(X), 7)
    sums = np.sum(probs, axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)

    # Feature importances should be populated
    assert len(rf.feature_importances) > 0


def test_lightgbm_classifier(synthetic_training_data):
    """LightGBM classifier fits, predicts probabilities summing to 1.0, and attributes features."""
    X, y = synthetic_training_data
    lgb = LightGBMRegimeClassifier(n_estimators=20, max_depth=4, random_state=42)
    lgb.fit(X, y)

    assert lgb.is_fitted
    probs = lgb.predict_proba(X)
    assert probs.shape == (len(X), 7)
    sums = np.sum(probs, axis=1)
    assert np.allclose(sums, 1.0, atol=1e-5)

    assert len(lgb.feature_importances) > 0


def test_critical_leakage_guard_in_regime_training():
    """Future observation targets must NEVER be allowed in regime classifier features."""
    leaked_data = pd.DataFrame({
        "raw_nwp_rainfall": [10.0, 20.0],
        "observed_rainfall_mm": [12.0, 22.0],  # CRITICAL LEAKAGE TARGET
        "heavy_rainfall": [0, 1],               # CRITICAL LEAKAGE TARGET
    })
    y = np.array([0, 1])

    rf = RandomForestRegimeClassifier(feature_columns=["raw_nwp_rainfall", "observed_rainfall_mm"])
    with pytest.raises(DataLeakageError):
        rf.fit(leaked_data, y)

    lgb = LightGBMRegimeClassifier(feature_columns=["raw_nwp_rainfall", "heavy_rainfall"])
    with pytest.raises(DataLeakageError):
        lgb.fit(leaked_data, y)
