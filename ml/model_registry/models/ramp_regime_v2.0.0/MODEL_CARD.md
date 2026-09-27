# MODEL CARD: ramp_regime_v2.0.0

## 1. Model Overview
- **Model Identifier:** `ramp_regime_v2.0.0`
- **Model Type:** `WEATHER_REGIME_CLASSIFIER`
- **Lifecycle Status:** `DEVELOPMENT`
- **Data Mode:** `SYNTHETIC_DEMO`
- **Dataset Version:** `ramp_dataset_real_v1.0.0`
- **Feature Schema Version:** `ramp_features_v1.0.0`
- **Target Schema Version:** `ramp_targets_v1.0.0`
- **Model SHA-256 Checksum:** `5237e3a5fed42abacb52b607bd1cf13d0ae3d8da2e8b30b060ce7fa8da9a4fc3`

## 2. Intended Meteorological Purpose
Post-processing of numerical weather prediction (NWP) rainfall forecasts over India
using regime-conditioned statistical machine learning. Enforces physical rainfall non-negativity
and multi-threshold probability monotonicity.

## 3. Training & Validation Gate Audit
- **All 12 Gates Passed:** `True`
- **Synthetic Mode Guard Active:** `True`
- **Production Promotion Eligible:** `False`

### Gate Status Table
| Promotion Gate | Status |
|---|---|
| `DATASET_VALID` | **PASS** |
| `LEAKAGE_FREE` | **PASS** |
| `FEATURE_SCHEMA_VALID` | **PASS** |
| `TARGET_SCHEMA_VALID` | **PASS** |
| `TEMPORAL_SPLIT_VALID` | **PASS** |
| `TRAINING_COMPLETED` | **PASS** |
| `VALIDATION_COMPLETED` | **PASS** |
| `TEST_EVALUATION_COMPLETED` | **PASS** |
| `CALIBRATION_COMPLETED` | **PASS** |
| `MONOTONICITY_VALID` | **PASS** |
| `PROVENANCE_COMPLETE` | **PASS** |
| `CHECKSUM_VALID` | **PASS** |

## 4. Summary Verification Metrics
```json
{
  "accuracy": 0.1304,
  "balanced_accuracy": 0.3333,
  "macro_f1": 0.1714,
  "per_class": {
    "ACTIVE_MONSOON": {
      "support": 3,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "BREAK_MONSOON": {
      "support": 0,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "LOW_DEPRESSION": {
      "support": 0,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "COASTAL": {
      "support": 8,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "OROGRAPHIC": {
      "support": 0,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "WESTERN_DISTURBANCE": {
      "support": 0,
      "status": "SAMPLE_LIMITED",
      "precision": null,
      "recall": null,
      "f1": null
    },
    "TRANSITION_OTHER": {
      "support": 12,
      "status": "VALIDATED",
      "precision": 0.0,
      "recall": 0.0,
      "f1": 0.0
    }
  },
  "confusion_matrix": [
    [
      3,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    [
      1,
      7,
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    [
      0,
      0,
      12,
      0,
      0,
      0,
      0
    ]
  ],
  "class_names": [
    "ACTIVE_MONSOON",
    "BREAK_MONSOON",
    "LOW_DEPRESSION",
    "COASTAL",
    "OROGRAPHIC",
    "WESTERN_DISTURBANCE",
    "TRANSITION_OTHER"
  ],
  "test_sample_count": 23
}
```

## 5. Known Limitations & Scientific Honesty Notice
Trained in `SYNTHETIC_DEMO` mode. **WARNING:** Because authoritative NCMRWF/IMD training datasets are not mounted in this environment, this model artifact is strictly classified as DEVELOPMENT and must NOT be used for real operational forecasting.

---
*NCMRWF / MoES Regime-Aware Mixture-of-Experts (RAMP) Project*