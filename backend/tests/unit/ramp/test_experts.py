"""
Unit Tests: 7 Specialized Regime Experts
SIH26080 | RAMP Mixture-of-Experts
"""

import numpy as np
import pandas as pd
import pytest

from ml.dataset.leakage_guard import DataLeakageError, TargetLeakageError
from ml.ramp.experts import (
    ActiveMonsoonExpert,
    BreakMonsoonExpert,
    CoastalExpert,
    LowDepressionExpert,
    OrographicExpert,
    RegimeExpert,
    TransitionOtherExpert,
    WesternDisturbanceExpert,
)
from ml.regimes.definitions import WeatherRegime


@pytest.fixture
def synthetic_training_data():
    np.random.seed(42)
    n = 30
    cols = RegimeExpert.DEFAULT_FEATURE_COLUMNS
    data = {c: np.random.uniform(0.0, 50.0, size=n) for c in cols}
    df_X = pd.DataFrame(data)
    y = np.random.exponential(scale=10.0, size=n)
    return df_X, y


def test_expert_initialization():
    expert = RegimeExpert(regime=WeatherRegime.ACTIVE_MONSOON)
    assert expert.regime_name == "ACTIVE_MONSOON"
    assert expert.status == "INITIALIZED"
    assert not expert.is_fitted
    assert expert.use_log1p_target is True


def test_expert_fit_and_predict(synthetic_training_data):
    df_X, y = synthetic_training_data
    expert = RegimeExpert(regime=WeatherRegime.ACTIVE_MONSOON, min_samples_to_train=5)
    expert.fit(df_X, y, split_label="TRAIN")

    assert expert.is_fitted
    assert expert.status == "TRAINED"
    assert expert.train_sample_count == len(df_X)

    preds = expert.predict(df_X)
    assert len(preds) == len(df_X)
    # Physical non-negativity invariant: R >= 0.0 mm
    assert (preds >= 0.0).all()
    assert np.all(np.isfinite(preds))


def test_expert_insufficient_samples():
    expert = RegimeExpert(regime=WeatherRegime.COASTAL, min_samples_to_train=10)
    df_X = pd.DataFrame({c: [1.0, 2.0] for c in RegimeExpert.DEFAULT_FEATURE_COLUMNS})
    y = np.array([5.0, 10.0])

    expert.fit(df_X, y, split_label="TRAIN")
    assert not expert.is_fitted
    assert expert.status == "INSUFFICIENT_DATA"

    with pytest.raises(RuntimeError):
        expert.predict(df_X)


def test_expert_leakage_guard_rejects_non_train_splits(synthetic_training_data):
    df_X, y = synthetic_training_data
    expert = RegimeExpert(regime=WeatherRegime.BREAK_MONSOON)

    with pytest.raises(DataLeakageError):
        expert.fit(df_X, y, split_label="VALIDATION")

    with pytest.raises(DataLeakageError):
        expert.fit(df_X, y, split_label="TEST")


def test_expert_leakage_guard_rejects_target_columns(synthetic_training_data):
    df_X, y = synthetic_training_data
    df_contaminated = df_X.copy()
    df_contaminated["observed_rainfall_mm"] = y

    expert = RegimeExpert(regime=WeatherRegime.LOW_DEPRESSION, feature_columns=list(df_contaminated.columns))
    with pytest.raises(TargetLeakageError):
        expert.fit(df_contaminated, y, split_label="TRAIN")


def test_all_seven_expert_subclasses():
    classes = [
        (ActiveMonsoonExpert, WeatherRegime.ACTIVE_MONSOON),
        (BreakMonsoonExpert, WeatherRegime.BREAK_MONSOON),
        (LowDepressionExpert, WeatherRegime.LOW_DEPRESSION),
        (CoastalExpert, WeatherRegime.COASTAL),
        (OrographicExpert, WeatherRegime.OROGRAPHIC),
        (WesternDisturbanceExpert, WeatherRegime.WESTERN_DISTURBANCE),
        (TransitionOtherExpert, WeatherRegime.TRANSITION_OTHER),
    ]
    for cls, expected_regime in classes:
        exp = cls()
        assert exp.regime == expected_regime
        assert exp.regime_name == expected_regime.value
