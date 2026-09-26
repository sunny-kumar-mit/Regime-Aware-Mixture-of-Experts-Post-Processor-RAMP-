"""
RAMP Regime Classifier Training & Evaluation Pipeline
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Orchestrates Phase 4 model training:
  1. Ingests Phase 3 Parquet splits (TRAIN, VAL, TEST).
  2. Generates audited weak labels on TRAIN and VAL.
  3. Trains Rule-based baseline, Random Forest, and LightGBM models.
  4. Fits multi-class calibration strictly on VALIDATION split.
  5. Evaluates models on held-out TEST partition.
  6. Exports model artifacts, metrics, and REGIME_MODEL_CARD.md.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from ml.feature_registry import feature_registry
from ml.regimes.calibration import RegimeCalibrator
from ml.regimes.classifier import (
    LightGBMRegimeClassifier,
    RandomForestRegimeClassifier,
    RuleBasedBaselineClassifier,
)
from ml.regimes.definitions import (
    INT_TO_REGIME,
    REGIME_ORDER,
    REGIME_TO_INT,
    WeatherRegime,
)
from ml.regimes.model_registry import RegimeModelMetadata, RegimeModelRegistry
from ml.regimes.transition import RegimeTransitionDetector
from ml.regimes.weak_labeler import RegimeLabeler


def train_regime_models(
    dataset_dir: Path = Path("data/processed/training/ramp_dataset_v0.3.0"),
    models_dir: Path = Path("data/models/regime"),
    model_version: str = "0.1.0",
) -> Dict[str, Any]:
    """
    Executes end-to-end training and evaluation for Phase 4 regime intelligence.
    """
    train_path = dataset_dir / "train.parquet"
    val_path = dataset_dir / "val.parquet"
    test_path = dataset_dir / "test.parquet"

    if not train_path.exists() or not val_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            f"Phase 3 training partitions not found in {dataset_dir}. "
            "Run 'python -m ml.dataset build' first."
        )

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)

    # Step 1: Weak label generation
    labeler = RegimeLabeler()
    train_labeled = labeler.generate_weak_labels(train_df)
    val_labeled = labeler.generate_weak_labels(val_df)
    test_labeled = labeler.generate_weak_labels(test_df)

    # Determine predictor features X (Phase 3 predictors only, NEVER targets)
    all_specs = feature_registry.list_features()
    candidate_features = [
        f.name for f in all_specs
        if f.name in train_df.columns and f.leakage_risk == "none"
    ]

    y_train = np.array([REGIME_TO_INT.get(lbl, 6) for lbl in train_labeled["regime_label"]])
    y_val = np.array([REGIME_TO_INT.get(lbl, 6) for lbl in val_labeled["regime_label"]])
    y_test = np.array([REGIME_TO_INT.get(lbl, 6) for lbl in test_labeled["regime_label"]])

    # Step 2: Model Training
    # Candidate 1: Rule-Based Physics Baseline
    rule_model = RuleBasedBaselineClassifier()
    rule_model.fit(train_labeled[candidate_features], y_train)

    # Candidate 2: Random Forest
    rf_model = RandomForestRegimeClassifier(
        n_estimators=100, max_depth=10, random_state=2026080, feature_columns=candidate_features
    )
    rf_model.fit(train_labeled[candidate_features], y_train)

    # Candidate 3: LightGBM
    lgb_model = LightGBMRegimeClassifier(
        n_estimators=100, learning_rate=0.05, max_depth=6, random_state=2026080, feature_columns=candidate_features
    )
    lgb_model.fit(train_labeled[candidate_features], y_train)

    # Step 3: Probability Calibration on VALIDATION partition only
    val_uncal_probs = lgb_model.predict_proba(val_labeled[candidate_features])
    calibrator = RegimeCalibrator(method="isotonic")
    calibrator.fit(val_uncal_probs, y_val, split_label="VALIDATION")

    # Step 4: Held-out TEST Set Evaluation
    test_X = test_labeled[candidate_features]
    raw_test_probs = lgb_model.predict_proba(test_X)
    cal_test_probs = calibrator.calibrate(raw_test_probs)
    y_pred = np.argmax(cal_test_probs, axis=1)

    # Metrics
    acc = float(accuracy_score(y_test, y_pred))
    bal_acc = float(balanced_accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    uncal_diag = RegimeCalibrator.evaluate_calibration(raw_test_probs, y_test)
    cal_diag = RegimeCalibrator.evaluate_calibration(cal_test_probs, y_test)

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred, labels=list(range(7))).tolist()

    # Regime-wise breakdown
    rep = classification_report(
        y_test, y_pred, labels=list(range(7)), target_names=[r.value for r in REGIME_ORDER], output_dict=True, zero_division=0
    )

    regime_wise = {}
    for r in REGIME_ORDER:
        val_name = r.value
        if val_name in rep:
            regime_wise[val_name] = {
                "precision": round(float(rep[val_name]["precision"]), 4),
                "recall": round(float(rep[val_name]["recall"]), 4),
                "f1_score": round(float(rep[val_name]["f1-score"]), 4),
                "support": int(rep[val_name]["support"]),
            }

    # Step 5: Save Model to Registry
    model_id = f"regime_lgbm_v{model_version}"
    metadata = RegimeModelMetadata(
        model_id=model_id,
        model_type="LightGBM_Multiclass_Classifier",
        version=model_version,
        dataset_id=dataset_dir.name,
        dataset_version=dataset_dir.name.replace("ramp_dataset_v", ""),
        training_period={
            "start": train_df["forecast_valid_time"].min().isoformat() if "forecast_valid_time" in train_df.columns else "",
            "end": train_df["forecast_valid_time"].max().isoformat() if "forecast_valid_time" in train_df.columns else "",
        },
        validation_period={
            "start": val_df["forecast_valid_time"].min().isoformat() if "forecast_valid_time" in val_df.columns else "",
            "end": val_df["forecast_valid_time"].max().isoformat() if "forecast_valid_time" in val_df.columns else "",
        },
        test_period={
            "start": test_df["forecast_valid_time"].min().isoformat() if "forecast_valid_time" in test_df.columns else "",
            "end": test_df["forecast_valid_time"].max().isoformat() if "forecast_valid_time" in test_df.columns else "",
        },
        features=candidate_features,
        label_source="WEAK_RULE",
        calibration_method="isotonic",
        hyperparameters={"n_estimators": 100, "learning_rate": 0.05, "max_depth": 6, "class_weight": "balanced"},
        metrics={
            "accuracy": round(acc, 4),
            "balanced_accuracy": round(bal_acc, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "brier_score_uncalibrated": uncal_diag["brier_score"],
            "brier_score_calibrated": cal_diag["brier_score"],
            "log_loss_uncalibrated": uncal_diag["log_loss"],
            "log_loss_calibrated": cal_diag["log_loss"],
        },
        regime_wise_metrics=regime_wise,
        data_mode="SYNTHETIC_DEMO",
    )

    reg = RegimeModelRegistry(models_dir=models_dir)
    target_model_dir = reg.save_model(lgb_model, calibrator, metadata)

    # Step 6: Transition Analysis over test set sequence
    detector = RegimeTransitionDetector()
    time_series = [t.isoformat() for t in test_df["forecast_valid_time"]] if "forecast_valid_time" in test_df.columns else [f"t_{i}" for i in range(len(test_df))]
    transition_report = detector.detect_transitions(time_series[:15], cal_test_probs[:15].tolist())

    # Step 7: Export JSON Reports
    with open(target_model_dir / "regime_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metadata.metrics, f, indent=2)

    with open(target_model_dir / "regime_confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump({"labels": [r.value for r in REGIME_ORDER], "matrix": cm}, f, indent=2)

    with open(target_model_dir / "regime_calibration.json", "w", encoding="utf-8") as f:
        json.dump({
            "calibration_method": "isotonic",
            "fitted_on": "VALIDATION",
            "uncalibrated": uncal_diag,
            "calibrated": cal_diag,
        }, f, indent=2)

    with open(target_model_dir / "regime_transition_report.json", "w", encoding="utf-8") as f:
        json.dump(transition_report, f, indent=2)

    # Regime distribution across splits
    dist = {
        "TRAIN": {r.value: int((train_labeled["regime_label"] == r.value).sum()) for r in REGIME_ORDER},
        "VALIDATION": {r.value: int((val_labeled["regime_label"] == r.value).sum()) for r in REGIME_ORDER},
        "TEST": {r.value: int((test_labeled["regime_label"] == r.value).sum()) for r in REGIME_ORDER},
    }
    with open(target_model_dir / "regime_distribution.json", "w", encoding="utf-8") as f:
        json.dump(dist, f, indent=2)

    # Generate REGIME_MODEL_CARD.md
    card_text = f"""# RAMP Model Card: {metadata.model_id}

**Model Architecture:** LightGBM Multi-Class Classifier + Isotonic Calibration  
**Model Version:** `{metadata.version}`  
**Dataset Version:** `{metadata.dataset_version}`  
**Operational Mode:** `SYNTHETIC_DEMO` (Real Training Data Not Available)  
**Calibration Fitted Split:** `VALIDATION` (Zero Test Set Contamination)  

---

## 1. Intended Use
Provides probabilistic weather regime classification across 7 canonical monsoon regimes.
Feeds directly into Phase 6 (RAMP Mixture-of-Experts) soft blending gates.

---

## 2. Test Set Performance (Held-out Chronological Test Partition)

> ⚠️ **SYNTHETIC DEMONSTRATION NOTICE**  
> Metrics below are computed on synthetic demonstration data. They validate pipeline integrity, probabilistic calibration, and soft gating mechanics. They MUST NOT be cited as real-world atmospheric accuracy.

| Metric | Score | Description |
| :--- | :--- | :--- |
| **Accuracy** | {metadata.metrics.get('accuracy', 0.0):.4f} | Overall top-1 classification accuracy |
| **Balanced Accuracy** | {metadata.metrics.get('balanced_accuracy', 0.0):.4f} | Unweighted mean of recall per class |
| **Macro F1** | {metadata.metrics.get('macro_f1', 0.0):.4f} | Unweighted harmonic mean of precision and recall |
| **Weighted F1** | {metadata.metrics.get('weighted_f1', 0.0):.4f} | Support-weighted F1 across all classes |
| **Brier Score (Calibrated)** | {metadata.metrics.get('brier_score_calibrated', 0.0):.4f} | Mean squared probability error (Lower is better) |
| **Log Loss (Calibrated)** | {metadata.metrics.get('log_loss_calibrated', 0.0):.4f} | Cross-entropy loss on held-out test data |

---

## 3. Regime-Wise Performance

| Regime | Precision | Recall | F1-Score | Support |
| :--- | :--- | :--- | :--- | :--- |
"""
    for reg, stats in regime_wise.items():
        card_text += f"| `{reg}` | {stats['precision']:.3f} | {stats['recall']:.3f} | {stats['f1_score']:.3f} | {stats['support']} |\n"

    card_text += """
---

## 4. Probabilistic Uncertainty & Entropy
Model posteriors provide Shannon entropy:
$$H(p) = -\\sum_{i=1}^7 p_i \\log_2(p_i)$$
Normalized entropy $H_{\\text{norm}} \\in [0, 1]$ categorizes model state into `LOW`, `MEDIUM`, or `HIGH` uncertainty.
"""

    with open(target_model_dir / "REGIME_MODEL_CARD.md", "w", encoding="utf-8") as f:
        f.write(card_text)

    # Also copy REGIME_MODEL_CARD.md to project root or docs
    with open(Path("REGIME_MODEL_CARD.md"), "w", encoding="utf-8") as f:
        f.write(card_text)

    return {
        "model_id": model_id,
        "metadata": metadata,
        "metrics": metadata.metrics,
        "regime_wise": regime_wise,
        "confusion_matrix": cm,
        "saved_path": target_model_dir,
    }
