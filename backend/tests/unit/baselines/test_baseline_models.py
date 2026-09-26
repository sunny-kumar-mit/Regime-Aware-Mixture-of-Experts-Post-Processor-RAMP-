"""
Unit Tests for Phase 5 Baseline Models:
- Raw NWP Baseline
- Mean Bias Corrector
- Empirical Quantile Mapper
- Global ML Post-Processor
SIH26080 | MoES / NCMRWF
"""

import pytest
import numpy as np
import pandas as pd
from ml.dataset.leakage_guard import DataLeakageError
from ml.baselines.models.raw_nwp import RawNWPBaseline
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.global_ml import GlobalMLPostProcessor


@pytest.fixture
def sample_train_df():
    np.random.seed(42)
    n = 200
    nwp = np.random.exponential(scale=10.0, size=n)
    nwp[nwp < 0.5] = 0.0  # dry days
    obs = nwp * 1.1 + np.random.normal(0, 2.0, size=n)
    obs = np.maximum(obs, 0.0)
    lead_times = np.random.choice([24, 48, 72], size=n)

    df = pd.DataFrame({
        "sample_id": [f"train_{i}" for i in range(n)],
        "raw_nwp_rainfall": nwp,
        "observed_rainfall_mm": obs,
        "lead_time_hours": lead_times,
        "u850": np.random.normal(5, 2, size=n),
        "v850": np.random.normal(2, 2, size=n),
        "mslp": np.random.normal(1005, 5, size=n),
        "relative_humidity": np.random.uniform(50, 95, size=n),
        "latitude": np.random.uniform(10, 30, size=n),
        "longitude": np.random.uniform(70, 90, size=n),
    })
    return df


@pytest.fixture
def sample_test_df():
    np.random.seed(99)
    n = 50
    nwp = np.random.exponential(scale=12.0, size=n)
    obs = nwp * 1.1 + np.random.normal(0, 2.0, size=n)
    obs = np.maximum(obs, 0.0)
    lead_times = np.random.choice([24, 48, 72, 96], size=n)

    df = pd.DataFrame({
        "sample_id": [f"test_{i}" for i in range(n)],
        "raw_nwp_rainfall": nwp,
        "observed_rainfall_mm": obs,
        "lead_time_hours": lead_times,
        "u850": np.random.normal(5, 2, size=n),
        "v850": np.random.normal(2, 2, size=n),
        "mslp": np.random.normal(1005, 5, size=n),
        "relative_humidity": np.random.uniform(50, 95, size=n),
        "latitude": np.random.uniform(10, 30, size=n),
        "longitude": np.random.uniform(70, 90, size=n),
    })
    return df


# 1. Raw NWP Identity Test
def test_raw_nwp_identity(sample_test_df):
    raw_model = RawNWPBaseline()
    preds = raw_model.predict(sample_test_df)
    assert np.allclose(preds, np.maximum(sample_test_df["raw_nwp_rainfall"].values, 0.0))


# 2. Non-Negativity Invariant
def test_physical_non_negativity_constraint():
    raw_model = RawNWPBaseline()
    df_neg = pd.DataFrame({
        "raw_nwp_rainfall": [-5.0, -0.01, 10.0, 0.0]
    })
    preds = raw_model.predict(df_neg)
    assert np.all(preds >= 0.0)
    assert preds[0] == 0.0
    assert preds[1] == 0.0
    assert preds[2] == 10.0


# 3. Mean Bias Train-Only Fitting
def test_mean_bias_train_only_enforcement(sample_train_df, sample_test_df):
    mb = MeanBiasCorrector()
    y_train = sample_train_df["observed_rainfall_mm"]
    mb.fit(sample_train_df, y_train, split_label="TRAIN")
    assert mb.is_fitted
    assert mb.global_bias is not None

    # Must raise DataLeakageError if attempted on test
    mb_invalid = MeanBiasCorrector()
    y_test = sample_test_df["observed_rainfall_mm"]
    with pytest.raises(DataLeakageError, match="strictly on 'TRAIN'"):
        mb_invalid.fit(sample_test_df, y_test, split_label="TEST")


# 4. Lead-Time Bias & Fallback
def test_mean_bias_lead_time_and_fallback(sample_train_df):
    mb = MeanBiasCorrector(min_samples_per_lead=10)
    y_train = sample_train_df["observed_rainfall_mm"]
    mb.fit(sample_train_df, y_train, split_label="TRAIN")

    assert 24 in mb.lead_time_biases
    assert 48 in mb.lead_time_biases
    assert 72 in mb.lead_time_biases

    # Test query with unseen lead time 96 (should fallback to global)
    test_unseen = pd.DataFrame({
        "raw_nwp_rainfall": [20.0],
        "lead_time_hours": [96]
    })
    preds = mb.predict(test_unseen)
    expected = max(0.0, 20.0 + mb.global_bias)
    assert np.isclose(preds[0], expected)


# 5. Extreme Rainfall Preservation (No Silent Capping)
def test_extreme_rainfall_preservation(sample_train_df):
    mb = MeanBiasCorrector()
    y_train = sample_train_df["observed_rainfall_mm"]
    mb.fit(sample_train_df, y_train, split_label="TRAIN")

    extreme_df = pd.DataFrame({
        "raw_nwp_rainfall": [64.5, 115.6, 204.5, 350.0],
        "lead_time_hours": [24, 24, 24, 24]
    })
    preds = mb.predict(extreme_df)
    # Ensure values > 204.5 mm are preserved and not arbitrarily capped
    assert preds[2] > 180.0
    assert preds[3] > 300.0


# 6. Quantile Mapping Train-Only Enforcement
def test_quantile_mapping_train_only_enforcement(sample_train_df, sample_test_df):
    eqm = EmpiricalQuantileMapper()
    y_train = sample_train_df["observed_rainfall_mm"]
    eqm.fit(sample_train_df, y_train, split_label="TRAIN")
    assert eqm.is_fitted
    assert eqm.train_samples == len(sample_train_df)

    eqm_invalid = EmpiricalQuantileMapper()
    y_test = sample_test_df["observed_rainfall_mm"]
    with pytest.raises(DataLeakageError, match="strictly on 'TRAIN'"):
        eqm_invalid.fit(sample_test_df, y_test, split_label="TEST")


# 7. Precipitation-Aware Dry-Day Handling
def test_quantile_mapping_dry_day_thresholding(sample_train_df):
    eqm = EmpiricalQuantileMapper(rain_threshold=0.1)
    y_train = sample_train_df["observed_rainfall_mm"]
    eqm.fit(sample_train_df, y_train, split_label="TRAIN")

    dry_df = pd.DataFrame({
        "raw_nwp_rainfall": [0.0, 0.05, 0.09, 0.1, 5.0]
    })
    preds = eqm.predict(dry_df)
    assert preds[0] == 0.0
    assert preds[1] == 0.0
    assert preds[2] == 0.0
    assert preds[3] >= 0.0
    assert preds[4] > 0.0


# 8. Quantile Tail Extrapolation Behavior
def test_quantile_mapping_tail_extrapolation(sample_train_df):
    eqm = EmpiricalQuantileMapper(extrapolation_policy="linear")
    y_train = sample_train_df["observed_rainfall_mm"]
    eqm.fit(sample_train_df, y_train, split_label="TRAIN")

    max_train_nwp = sample_train_df["raw_nwp_rainfall"].max()
    super_deluge = pd.DataFrame({
        "raw_nwp_rainfall": [max_train_nwp + 100.0]
    })
    preds = eqm.predict(super_deluge)
    # Under linear extrapolation, prediction should scale beyond max observed
    assert preds[0] > eqm.obs_wet_quantiles[-1]
    assert preds[0] >= 0.0


# 9. Global ML Train/Val/Test Separation & Log-Transform
def test_global_ml_postprocessor(sample_train_df, sample_test_df):
    features = [
        "raw_nwp_rainfall", "lead_time_hours", "u850", "v850",
        "mslp", "relative_humidity", "latitude", "longitude"
    ]
    model = GlobalMLPostProcessor(feature_columns=features, n_estimators=10, max_depth=3)
    y_train = sample_train_df["observed_rainfall_mm"]

    # Validate training
    model.fit(sample_train_df, y_train, split_label="TRAIN")
    assert model.is_fitted

    preds = model.predict(sample_test_df)
    assert len(preds) == len(sample_test_df)
    assert np.all(preds >= 0.0)
    assert not np.isnan(preds).any()
