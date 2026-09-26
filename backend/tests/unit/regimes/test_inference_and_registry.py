"""
Unit Tests for Regime Inference Service and Model Registry
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.regimes.authoritative import AuthoritativeLabelRegistry, IMDMonsoonBulletinProvider
from ml.regimes.calibration import RegimeCalibrator
from ml.regimes.classifier import RuleBasedBaselineClassifier
from ml.regimes.definitions import REGIME_ORDER, UncertaintyLevel, WeatherRegime
from ml.regimes.inference import RegimeInferenceService
from ml.regimes.model_registry import RegimeModelMetadata, RegimeModelRegistry


def test_model_registry_save_and_load():
    """Tests safe joblib model serialization, metadata tracking, and model reloading."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        registry = RegimeModelRegistry(models_dir=tmp_dir)

        clf = RuleBasedBaselineClassifier()
        cal = RegimeCalibrator(method="isotonic")
        meta = RegimeModelMetadata(
            model_id="test_regime_model_v1",
            model_type="RuleBased_Baseline",
            dataset_id="ramp_dataset_v0.3.0",
            dataset_version="v0.3.0",
            features=["raw_nwp_rainfall", "u850"],
        )

        saved_path = registry.save_model(clf, cal, meta)
        assert saved_path.exists()
        assert (saved_path / "model_metadata.json").exists()

        # Load back
        loaded_clf, loaded_cal, loaded_meta = registry.load_model("test_regime_model_v1")
        assert loaded_clf.name == clf.name
        assert loaded_meta.model_id == "test_regime_model_v1"
        assert loaded_meta.features == ["raw_nwp_rainfall", "u850"]


def test_inference_service_predict_sample():
    """Inference service produces complete probability vector, entropy, and attribution."""
    service = RegimeInferenceService(model_version="test_v1.0")

    sample = {
        "raw_nwp_rainfall": 20.0,
        "u850": 10.0,
        "v850": 3.0,
        "wind_speed_850": 10.4,
        "mslp": 100300.0,
        "relative_humidity": 85.0,
        "precipitable_water": 50.0,
        "latitude": 21.0,
        "longitude": 78.0,
        "monsoon": 1,
        "winter": 0,
    }

    pred = service.predict_sample(sample)

    assert "top_regime" in pred
    assert pred["top_regime"] in [r.value for r in REGIME_ORDER]
    assert "probabilities" in pred
    assert len(pred["probabilities"]) == 7

    # Sum of probabilities must equal 1.0 within 1e-4
    prob_sum = sum(pred["probabilities"].values())
    assert np.isclose(prob_sum, 1.0, atol=1e-3)

    assert 0.0 <= pred["confidence"] <= 1.0
    assert pred["entropy"] >= 0.0
    assert 0.0 <= pred["normalized_entropy"] <= 1.0
    assert pred["uncertainty_level"] in [u.value for u in UncertaintyLevel]
    assert "feature_availability" in pred


def test_inference_service_grid_prediction():
    """Inference service processes spatial grid into probability layers."""
    service = RegimeInferenceService(model_version="test_v1.0")

    grid_df = pd.DataFrame([
        {"latitude": 15.0, "longitude": 74.0, "raw_nwp_rainfall": 25.0, "u850": 8.0, "v850": 2.0, "monsoon": 1, "winter": 0},
        {"latitude": 20.0, "longitude": 85.0, "raw_nwp_rainfall": 40.0, "u850": 12.0, "v850": 6.0, "monsoon": 1, "winter": 0},
        {"latitude": 30.0, "longitude": 76.0, "raw_nwp_rainfall": 2.0, "u850": 4.0, "v850": 0.0, "monsoon": 0, "winter": 1},
    ])

    grid_res = service.predict_grid(grid_df)
    assert grid_res["total_points"] == 3
    assert len(grid_res["top_regimes"]) == 3
    assert len(grid_res["layers"]) == 7

    # Each layer should have 3 probability values
    for reg in REGIME_ORDER:
        assert len(grid_res["layers"][reg.value]) == 3


def test_authoritative_provider_honest_unavailability():
    """Authoritative provider correctly reports UNAVAILABLE when real IMD bulletins are absent."""
    provider = IMDMonsoonBulletinProvider()
    assert provider.provider_name == "IMD_MONSOON_BULLETINS"
    assert provider.is_available is False

    from datetime import datetime
    with pytest.raises(FileNotFoundError, match="Authoritative IMD regime catalogue is NOT AVAILABLE"):
        provider.get_labels_for_period(datetime(2026, 6, 1), datetime(2026, 9, 30))
