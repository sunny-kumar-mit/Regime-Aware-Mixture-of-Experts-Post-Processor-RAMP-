"""
Unit Tests for Phase 5 Diagnostics, Registry, and Inference Contracts
SIH26080 | MoES / NCMRWF
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import json

from ml.baselines.diagnostics.lead_time_stratification import LeadTimeStratifiedEvaluator
from ml.baselines.diagnostics.regime_stratification import RegimeStratifiedEvaluator
from ml.baselines.diagnostics.spatial_evaluation import SpatialEvaluator
from ml.baselines.model_registry import BaselineModelRegistry, BaselineModelMetadata
from ml.baselines.models.raw_nwp import RawNWPBaseline
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.inference import BaselineInferenceService, PredictionRecord
from ml.baselines.benchmark import BaselineBenchmarkEngine


@pytest.fixture
def eval_df():
    np.random.seed(42)
    n = 150
    obs = np.random.exponential(scale=10.0, size=n)
    nwp = obs * 0.9 + np.random.normal(0, 3.0, size=n)
    nwp = np.maximum(nwp, 0.0)

    regimes = [
        "ACTIVE_MONSOON",
        "BREAK_MONSOON",
        "LOW_DEPRESSION",
        "COASTAL",
        "OROGRAPHIC",
        "WESTERN_DISTURBANCE",
        "TRANSITION_OTHER",
    ]

    df = pd.DataFrame({
        "sample_id": [f"eval_{i}" for i in range(n)],
        "forecast_valid_time": ["2023-07-15T00:00:00Z"] * n,
        "latitude": np.random.choice([15.0, 20.0, 25.0], size=n),
        "longitude": np.random.choice([75.0, 80.0, 85.0], size=n),
        "lead_time_hours": np.random.choice([24, 48, 72, 96, 120], size=n),
        "observed_rainfall_mm": obs,
        "raw_nwp_rainfall": nwp,
        "raw_nwp": nwp,
        "mean_bias": np.maximum(nwp + 1.0, 0.0),
        "quantile_mapping": np.maximum(nwp * 1.05, 0.0),
        "global_ml": np.maximum(nwp * 0.98 + 0.5, 0.0),
        "regime_label": np.random.choice(regimes, size=n),
    })
    return df


def test_lead_time_stratification(eval_df):
    results = LeadTimeStratifiedEvaluator.evaluate(
        eval_df,
        model_names=["raw_nwp", "mean_bias"],
        lead_time_col="lead_time_hours",
        obs_col="observed_rainfall_mm",
    )
    assert "lead_time_diagnostics" in results
    diag = results["lead_time_diagnostics"]
    assert "Day_1_24h" in diag or 24 in diag or len(diag) > 0


def test_regime_stratification(eval_df):
    evaluator = RegimeStratifiedEvaluator()
    report = evaluator.evaluate(
        eval_df,
        model_names=["raw_nwp", "global_ml"],
        regime_col="regime_label",
        obs_col="observed_rainfall_mm",
    )
    assert "regime_diagnostics" in report
    diag = report["regime_diagnostics"]
    assert "ACTIVE_MONSOON" in diag
    assert "BREAK_MONSOON" in diag
    for regime_key in diag:
        assert "models" in diag[regime_key]
        assert "raw_nwp" in diag[regime_key]["models"]
        assert "global_ml" in diag[regime_key]["models"]


def test_spatial_evaluation(eval_df):
    results = SpatialEvaluator.evaluate_grid_points(
        eval_df,
        model_names=["raw_nwp", "mean_bias"],
        lat_col="latitude",
        lon_col="longitude",
        obs_col="observed_rainfall_mm",
    )
    assert "spatial_points" in results
    assert len(results["spatial_points"]) > 0
    pt = results["spatial_points"][0]
    assert "latitude" in pt
    assert "longitude" in pt
    assert "models" in pt


def test_model_registry_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = BaselineModelRegistry(models_dir=tmpdir)
        raw_model = RawNWPBaseline()
        metadata = BaselineModelMetadata(
            model_id="raw_nwp_test",
            model_type="RAW_NWP",
            dataset_version="v0.3.0",
            feature_schema_version="v1.0",
            training_period={"start": "2023-01-01", "end": "2023-08-31"},
            validation_period={"start": "2023-09-01", "end": "2023-09-15"},
            test_period={"start": "2023-09-16", "end": "2023-09-30"},
            lead_times=[24, 48, 72],
            thresholds=[0.1, 64.5, 115.6, 204.5],
            hyperparameters={},
            preprocessing_version="v1.0",
        )

        reg.save_model(raw_model, metadata)

        # Verify listed
        models = reg.list_models()
        assert len(models) == 1
        assert models[0].model_id == "raw_nwp_test"

        # Verify load
        loaded_model, loaded_meta = reg.load_model("raw_nwp_test")
        assert loaded_meta.model_id == "raw_nwp_test"
        assert isinstance(loaded_model, RawNWPBaseline)


def test_baseline_inference_service_and_contract(eval_df):
    raw_m = RawNWPBaseline()
    mb_m = MeanBiasCorrector()
    mb_m.global_bias = 0.5
    mb_m.is_fitted = True

    service = BaselineInferenceService(
        raw_nwp=raw_m,
        mean_bias=mb_m,
        dataset_version="v0.3.0",
        data_mode="SYNTHETIC_DEMO",
    )

    sample_row = eval_df.iloc[0]
    rec = service.predict_sample(sample_row)

    assert isinstance(rec, PredictionRecord)
    assert rec.sample_id == sample_row["sample_id"]
    assert rec.raw_nwp_prediction >= 0.0
    assert rec.mean_bias_prediction >= 0.0
    assert rec.data_mode == "SYNTHETIC_DEMO"
    assert np.isclose(rec.observed_rainfall, sample_row["observed_rainfall_mm"], atol=1e-2)
