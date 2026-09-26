"""
Unit Tests: RAMP Model Registry & Artifact Management
SIH26080 | RAMP Mixture-of-Experts
"""

import json
from pathlib import Path
import pytest

from ml.ramp.experts import RegimeExpert
from ml.ramp.model import RAMPModel
from ml.ramp.model_registry import RAMPModelMetadata, RAMPModelRegistry
from ml.regimes.definitions import REGIME_ORDER, WeatherRegime


def test_save_and_load_ramp_model(tmp_path):
    registry = RAMPModelRegistry(models_dir=tmp_path)

    # Initialize model with 7 experts
    model = RAMPModel(version="test_ramp_v1.0")

    meta = RAMPModelMetadata(
        ramp_model_id="test_ramp_v1.0",
        dataset_version="v0.3.0",
        phase4_model_version="regime_lgbm_v0.1.0",
        phase5_baseline_version="global_lgbm_v1",
        expert_versions={r.value: "v1" for r in REGIME_ORDER},
        expert_statuses={r.value: "INSUFFICIENT_DATA" for r in REGIME_ORDER},
    )

    saved_dir = registry.save_model(model, meta)
    assert saved_dir.exists()
    assert (saved_dir / "ramp_model_metadata.json").exists()
    assert (saved_dir / "experts").exists()

    # Load model back
    loaded_model, loaded_meta = registry.load_model("test_ramp_v1.0")
    assert loaded_model.version == "test_ramp_v1.0"
    assert loaded_meta.ramp_model_id == "test_ramp_v1.0"
    assert len(loaded_model.experts) == 7


def test_list_models(tmp_path):
    registry = RAMPModelRegistry(models_dir=tmp_path)
    assert len(registry.list_models()) == 0

    model = RAMPModel(version="ramp_v1")
    meta = RAMPModelMetadata(ramp_model_id="ramp_v1")
    registry.save_model(model, meta)

    models = registry.list_models()
    assert len(models) == 1
    assert models[0].ramp_model_id == "ramp_v1"


def test_load_nonexistent_model_raises(tmp_path):
    registry = RAMPModelRegistry(models_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        registry.load_model("nonexistent_model")
