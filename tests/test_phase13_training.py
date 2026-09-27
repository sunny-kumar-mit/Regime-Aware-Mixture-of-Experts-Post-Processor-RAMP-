"""
Phase 13 Comprehensive Test Suite: Model Retraining, Calibration & Model Registry
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Covers all 21 Part AF required test specifications + regression integrity:
1. test_dataset_gate
2. test_dataset_checksum
3. test_feature_schema
4. test_target_schema
5. test_temporal_split
6. test_no_future_leakage
7. test_baseline_training
8. test_global_model
9. test_regime_model
10. test_moe_model
11. test_extreme_model
12. test_monotonicity
13. test_probability_calibration
14. test_lead_time_metrics
15. test_regime_metrics
16. test_model_manifest
17. test_model_checksum
18. test_registry_versioning
19. test_model_promotion_gate
20. test_synthetic_mode_block
21. test_real_mode_detection
"""

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.training.baselines import BaselineSuite
from ml.training.calibration import ProbabilityCalibrator, compute_ece_mce
from ml.training.config import (
    FEATURE_SCHEMA_VERSION,
    PROMOTION_GATES,
    TARGET_SCHEMA_VERSION,
    ModelLifecycle,
)
from ml.training.dataset_gate import DatasetGate, RealTrainingEligibilityGate
from ml.training.dataset_loader import DatasetLoader
from ml.training.evaluation import (
    build_model_comparison_table,
    compute_contingency_table,
    evaluate_lead_times,
    evaluate_regimes,
    evaluate_threshold_suite,
)
from ml.training.extreme_models import ExtremeProbabilityModels
from ml.training.feature_contract import (
    APPROVED_PREDICTORS,
    FEATURE_NAMES,
    FeatureContractValidator,
    audit_predictor_dataframe,
)
from ml.training.global_model import GlobalPrecipitationModel
from ml.training.moe_model import RAMP_MoE_Model
from ml.training.monotonicity import MonotonicityVerifier
from ml.training.provenance import compute_file_sha256
from ml.training.regime_model import WeatherRegimeModel
from ml.training.registry import ModelOverwriteError, ModelRegistry
from ml.training.split import TemporalSplitVerifier
from ml.training.target_contract import TargetContractValidator

DATASET_DIR = "ml/datasets/real/ramp_dataset_real_v1.0.0"


@pytest.fixture(scope="module")
def dataset_splits():
    """Load train/val/test partitions from dataset loader (synthetic fixture)."""
    loader = DatasetLoader(DATASET_DIR)
    return loader.load_splits(use_synthetic_if_missing=True)


# 1. test_dataset_gate
def test_dataset_gate():
    res = DatasetGate.validate(DATASET_DIR)
    assert res["valid"] is True
    assert res["status"] == "DATASET_VALID"
    assert "reasons" in res


# 2. test_dataset_checksum
def test_dataset_checksum():
    checksum_file = Path(DATASET_DIR) / "checksum_manifest.json"
    assert checksum_file.exists()
    with open(checksum_file, "r", encoding="utf-8") as f:
        chk = json.load(f)
    assert "sha256" in chk or "checksums" in chk



# 3. test_feature_schema
def test_feature_schema(dataset_splits):
    X_train, _ = dataset_splits["train"]
    val = FeatureContractValidator.validate_features(X_train[FEATURE_NAMES])
    assert val["is_valid"] is True
    assert val["feature_count"] == 18
    assert val["schema_version"] == FEATURE_SCHEMA_VERSION
    assert len(val["missing_features"]) == 0


# 4. test_target_schema
def test_target_schema():
    sample_df = pd.DataFrame({
        "observed_rainfall_mm": [0.0, 10.5, 70.0, 120.0, 210.0],
        "rain_label": [0, 1, 1, 1, 1],
        "heavy_label": [0, 0, 1, 1, 1],
        "very_heavy_label": [0, 0, 0, 1, 1],
        "extreme_label": [0, 0, 0, 0, 1],
    })
    val = TargetContractValidator.validate_targets(sample_df)
    assert val["is_valid"] is True
    assert val["schema_version"] == TARGET_SCHEMA_VERSION


# 5. test_temporal_split
def test_temporal_split(dataset_splits):
    X_train, _ = dataset_splits["train"]
    X_val, _ = dataset_splits["val"]
    X_test, _ = dataset_splits["test"]
    split_res = TemporalSplitVerifier.verify(X_train, X_val, X_test)
    assert split_res["valid"] is True
    assert split_res["passed"] is True


# 6. test_no_future_leakage
def test_no_future_leakage():
    leak_df = pd.DataFrame({
        "precip_nwp_raw": [10.0],
        "future_observation": [5.0],
    })
    with pytest.raises(ValueError, match="CRITICAL LEAKAGE DETECTED"):
        audit_predictor_dataframe(leak_df)


# 7. test_baseline_training
def test_baseline_training(dataset_splits):
    X_train, y_train = dataset_splits["train"]
    X_test, _ = dataset_splits["test"]
    baselines = BaselineSuite(random_seed=42)
    baselines.fit(X_train, y_train)
    preds = baselines.predict_all(X_test)
    assert len(preds) == 6
    for model_name in ["raw_nwp", "simple_bias_correction", "linear_regression", "ridge_regression", "random_forest", "global_ml"]:
        assert model_name in preds
        assert len(preds[model_name]) == len(X_test)
        assert np.all(preds[model_name] >= 0.0)  # Non-negativity invariant


# 8. test_global_model
def test_global_model(dataset_splits):
    X_train, y_train = dataset_splits["train"]
    X_val, y_val = dataset_splits["val"]
    X_test, y_test = dataset_splits["test"]
    model = GlobalPrecipitationModel(n_estimators=20, random_seed=42)
    model.fit(X_train, y_train, X_val=X_val, y_val=y_val)
    preds = model.predict(X_test)
    assert len(preds) == len(X_test)
    assert np.all(preds >= 0.0)
    ev = model.evaluate(X_test, y_test)
    assert "overall" in ev
    assert "stratified" in ev
    assert "mae" in ev["overall"]
    assert "rmse" in ev["overall"]


# 9. test_regime_model
def test_regime_model(dataset_splits):
    X_train, y_train = dataset_splits["train"]
    X_test, _ = dataset_splits["test"]
    reg_train = np.where(y_train > 30.0, "ACTIVE_MONSOON", "TRANSITION_OTHER")
    model = WeatherRegimeModel(n_estimators=20, random_seed=42)
    model.fit(X_train, reg_train)
    proba = model.predict_proba(X_test)
    assert proba.shape == (len(X_test), 7)
    assert np.allclose(np.sum(proba, axis=1), 1.0)
    labels = model.predict(X_test)
    assert len(labels) == len(X_test)


# 10. test_moe_model
def test_moe_model(dataset_splits):
    X_train, y_train = dataset_splits["train"]
    X_test, y_test = dataset_splits["test"]
    reg_train = np.where(y_train > 30.0, "ACTIVE_MONSOON", "TRANSITION_OTHER")
    moe = RAMP_MoE_Model(random_seed=42)
    moe.fit(X_train, y_train, regimes_train=reg_train)
    preds = moe.predict(X_test)
    assert len(preds) == len(X_test)
    assert np.all(preds >= 0.0)
    ev = moe.evaluate(X_test, y_test, regimes_test=reg_train[: len(X_test)])
    assert "overall" in ev
    assert "expert_usage" in ev


# 11. test_extreme_model
def test_extreme_model(dataset_splits):
    X_train, y_train = dataset_splits["train"]
    X_test, y_test = dataset_splits["test"]
    ext = ExtremeProbabilityModels(random_seed=42)
    ext.fit(X_train, np.asarray(y_train))
    probs, mono = ext.predict_proba_dict(X_test)
    assert len(probs) == 4
    for col in ["prob_rain_0p1mm", "prob_heavy_64p5mm", "prob_very_heavy_115p6mm", "prob_extreme_204p5mm"]:
        assert col in probs
        assert np.all((probs[col] >= 0.0) & (probs[col] <= 1.0))
    ev = ext.evaluate(X_test, np.asarray(y_test))
    assert "thresholds" in ev
    assert "monotonicity" in ev


# 12. test_monotonicity
def test_monotonicity():
    # Valid non-increasing probabilities
    valid_probs = {
        "prob_rain_0p1mm": np.array([0.9, 0.8]),
        "prob_heavy_64p5mm": np.array([0.5, 0.4]),
        "prob_very_heavy_115p6mm": np.array([0.3, 0.2]),
        "prob_extreme_204p5mm": np.array([0.1, 0.05]),
    }
    audit = MonotonicityVerifier.audit(valid_probs)
    assert audit["is_monotonic"] is True
    assert audit["number_of_violations"] == 0

    # Violating probabilities
    viol_probs = {
        "prob_rain_0p1mm": np.array([0.2]),
        "prob_heavy_64p5mm": np.array([0.7]),  # Violation: 0.7 > 0.2
        "prob_very_heavy_115p6mm": np.array([0.1]),
        "prob_extreme_204p5mm": np.array([0.05]),
    }
    audit_v = MonotonicityVerifier.audit(viol_probs)
    assert audit_v["is_monotonic"] is False
    assert audit_v["number_of_violations"] == 1

    corrected, rep = MonotonicityVerifier.enforce(viol_probs)
    assert rep["is_monotonic"] is True
    assert corrected["prob_heavy_64p5mm"][0] <= corrected["prob_rain_0p1mm"][0]


# 13. test_probability_calibration
def test_probability_calibration():
    y_val_true = np.array([0, 0, 0, 1, 1, 1])
    y_val_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(y_val_prob, y_val_true)
    test_prob = np.array([0.15, 0.85])
    cal_prob = calibrator.predict(test_prob)
    assert len(cal_prob) == 2
    assert np.all((cal_prob >= 0.0) & (cal_prob <= 1.0))
    ece, mce, bins = compute_ece_mce(y_val_true, y_val_prob, n_bins=5)
    assert ece >= 0.0
    assert mce >= 0.0


# 14. test_lead_time_metrics
def test_lead_time_metrics(dataset_splits):
    X_test, y_test = dataset_splits["test"]
    df = X_test.copy()
    df["observed_rainfall"] = y_test
    df["raw_nwp"] = df["precip_nwp_raw"]
    res = evaluate_lead_times(df)
    assert "available_lead_times" in res
    assert "lead_time_metrics" in res


# 15. test_regime_metrics
def test_regime_metrics(dataset_splits):
    X_test, y_test = dataset_splits["test"]
    df = X_test.copy()
    df["observed_rainfall"] = y_test
    df["raw_nwp"] = df["precip_nwp_raw"]
    df["regime"] = np.where(y_test > 30.0, "ACTIVE_MONSOON", "TRANSITION_OTHER")
    res = evaluate_regimes(df)
    assert "regimes" in res


# 16. test_model_manifest
def test_model_manifest():
    reg = ModelRegistry()
    manifest = reg.get_model_manifest("ramp_moe_v2.0.0")
    assert manifest is not None
    assert manifest["model_id"] == "ramp_moe_v2.0.0"
    assert "lifecycle_status" in manifest
    assert "promotion_gates" in manifest


# 17. test_model_checksum
def test_model_checksum():
    model_bin = Path("ml/model_registry/models/ramp_moe_v2.0.0/model.bin")
    checksum_file = Path("ml/model_registry/models/ramp_moe_v2.0.0/checksum.sha256")
    assert model_bin.exists()
    assert checksum_file.exists()
    with open(checksum_file, "r", encoding="utf-8") as f:
        saved_checksum = f.read().split()[0]
    calc_checksum = compute_file_sha256(str(model_bin))
    assert saved_checksum == calc_checksum


# 18. test_registry_versioning
def test_registry_versioning():
    reg = ModelRegistry()
    models = reg.list_models()
    assert len(models) >= 4
    model_ids = [m["model_id"] for m in models]
    assert "ramp_global_v2.0.0" in model_ids
    assert "ramp_regime_v2.0.0" in model_ids
    assert "ramp_moe_v2.0.0" in model_ids
    assert "ramp_extreme_v2.0.0" in model_ids


# 19. test_model_promotion_gate
def test_model_promotion_gate():
    reg = ModelRegistry()
    # If all 12 gates pass and real data
    all_gates_pass = {g: True for g in PROMOTION_GATES}
    eval_real = reg.evaluate_gates(all_gates_pass, data_mode="REAL_OPERATIONAL")
    assert eval_real["all_gates_passed"] is True
    assert eval_real["promotion_eligible"] is True
    assert eval_real["recommended_lifecycle"] == ModelLifecycle.PRODUCTION_READY.value

    # If any gate fails
    failed_gate = dict(all_gates_pass)
    failed_gate["LEAKAGE_FREE"] = False
    eval_fail = reg.evaluate_gates(failed_gate, data_mode="REAL_OPERATIONAL")
    assert eval_fail["promotion_eligible"] is False
    assert eval_fail["recommended_lifecycle"] == ModelLifecycle.BLOCKED.value


# 20. test_synthetic_mode_block
def test_synthetic_mode_block():
    reg = ModelRegistry()
    all_gates_pass = {g: True for g in PROMOTION_GATES}
    # Crucial scientific integrity rule: SYNTHETIC_DEMO can NEVER be promoted to PRODUCTION_READY
    eval_synth = reg.evaluate_gates(all_gates_pass, data_mode="SYNTHETIC_DEMO")
    assert eval_synth["all_gates_passed"] is True
    assert eval_synth["synthetic_block_applied"] is True
    assert eval_synth["promotion_eligible"] is False
    assert eval_synth["recommended_lifecycle"] == ModelLifecycle.DEVELOPMENT.value


# 21. test_real_mode_detection
def test_real_mode_detection():
    elig = RealTrainingEligibilityGate.evaluate(DATASET_DIR)
    assert "real_data_available" in elig
    assert elig["real_data_available"] is False
    assert elig["real_training_deferred"] is True
    assert "Production real-data training deferred" in elig["message"]
