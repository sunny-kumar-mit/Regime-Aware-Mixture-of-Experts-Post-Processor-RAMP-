"""
Unit tests for PreprocessingPipeline: train-only fitting and identical application.
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.dataset.preprocessing import PreprocessingPipeline
from ml.schemas import ImputationStrategy


def test_preprocessing_fit_train_only():
    """Preprocessing must be fitted on TRAIN and reject fitting on other splits."""
    train_df = pd.DataFrame({
        "raw_nwp_rainfall": [10.0, 20.0, np.nan, 40.0],
        "temperature": [295.0, 300.0, 305.0, np.nan],
    })

    pipe = PreprocessingPipeline(imputation_strategy=ImputationStrategy.MEDIAN_TRAIN)
    pipe.fit(train_df, split_label="TRAIN")

    assert pipe.is_fitted
    assert pipe.fitted_split == "TRAIN"
    # Median of [10, 20, 40] is 20.0
    assert pipe.fitted_medians["raw_nwp_rainfall"] == 20.0

    # Leakage check: Reject fitting on VALIDATION
    with pytest.raises(ValueError, match="Data Leakage Violation"):
        pipe.fit(train_df, split_label="VALIDATION")


def test_preprocessing_identical_transform_on_test():
    """Test set must be imputed using TRAIN medians without updating statistics."""
    train_df = pd.DataFrame({"raw_nwp_rainfall": [10.0, 20.0, 30.0]})
    pipe = PreprocessingPipeline(imputation_strategy=ImputationStrategy.MEDIAN_TRAIN)
    pipe.fit(train_df, split_label="TRAIN")

    # In train: median is 20.0
    test_df = pd.DataFrame({"raw_nwp_rainfall": [np.nan, 100.0]})
    test_out = pipe.transform(test_df)

    # Missing value in test must be filled with TRAIN median (20.0), NOT test value
    assert test_out["raw_nwp_rainfall"].iloc[0] == 20.0
    assert test_out["raw_nwp_rainfall"].iloc[1] == 100.0


def test_preprocessing_manifest_serialization(tmp_path):
    """Manifest must serialize train-fitted parameters accurately."""
    train_df = pd.DataFrame({"temperature": [290.0, 300.0, 310.0]})
    pipe = PreprocessingPipeline(imputation_strategy=ImputationStrategy.MEDIAN_TRAIN)
    pipe.fit(train_df, split_label="TRAIN")

    manifest_file = tmp_path / "preprocessing_manifest.json"
    pipe.export_manifest(manifest_file)
    assert manifest_file.exists()

    manifest = pipe.get_manifest()
    assert manifest.fitted_on_split == "TRAIN"
    assert manifest.fitted_statistics["medians"]["temperature"] == 300.0
