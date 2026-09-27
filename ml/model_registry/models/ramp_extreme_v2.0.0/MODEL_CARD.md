# MODEL CARD: ramp_extreme_v2.0.0

## 1. Model Overview
- **Model Identifier:** `ramp_extreme_v2.0.0`
- **Model Type:** `EXTREME_PROBABILITY_MODELS`
- **Lifecycle Status:** `DEVELOPMENT`
- **Data Mode:** `SYNTHETIC_DEMO`
- **Dataset Version:** `ramp_dataset_real_v1.0.0`
- **Feature Schema Version:** `ramp_features_v1.0.0`
- **Target Schema Version:** `ramp_targets_v1.0.0`
- **Model SHA-256 Checksum:** `9f337b3ad14a6d2e3a2cf4648f7ca575e71e9a25cb2d31989bde31e5d8249f2a`

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
  "thresholds": {
    "rain_0p1mm": {
      "threshold_mm": 0.1,
      "event_count": 22,
      "non_event_count": 1,
      "prevalence": 0.95652,
      "status": "SAMPLE_LIMITED",
      "brier_score": null,
      "brier_skill_score": null,
      "roc_auc": null,
      "pr_auc": null,
      "ece": null,
      "mce": null
    },
    "heavy_64p5mm": {
      "threshold_mm": 64.5,
      "event_count": 3,
      "non_event_count": 20,
      "prevalence": 0.13043,
      "status": "SAMPLE_LIMITED",
      "brier_score": null,
      "brier_skill_score": null,
      "roc_auc": null,
      "pr_auc": null,
      "ece": null,
      "mce": null
    },
    "very_heavy_115p6mm": {
      "threshold_mm": 115.6,
      "event_count": 1,
      "non_event_count": 22,
      "prevalence": 0.04348,
      "status": "SAMPLE_LIMITED",
      "brier_score": null,
      "brier_skill_score": null,
      "roc_auc": null,
      "pr_auc": null,
      "ece": null,
      "mce": null
    },
    "extreme_204p5mm": {
      "threshold_mm": 204.5,
      "event_count": 0,
      "non_event_count": 23,
      "prevalence": 0.0,
      "status": "SAMPLE_LIMITED",
      "brier_score": null,
      "brier_skill_score": null,
      "roc_auc": null,
      "pr_auc": null,
      "ece": null,
      "mce": null
    }
  },
  "monotonicity": {
    "total_samples": 23,
    "number_of_violations": 0,
    "violation_rate": 0.0,
    "maximum_violation": 0.0,
    "is_monotonic": true,
    "violation_locations": [],
    "thresholds_evaluated": [
      0.1,
      64.5,
      115.6,
      204.5
    ],
    "correction_applied": "cumulative_min",
    "violations_before": 6,
    "max_violation_before": 0.13704
  },
  "test_sample_count": 23
}
```

## 5. Known Limitations & Scientific Honesty Notice
Trained in `SYNTHETIC_DEMO` mode. **WARNING:** Because authoritative NCMRWF/IMD training datasets are not mounted in this environment, this model artifact is strictly classified as DEVELOPMENT and must NOT be used for real operational forecasting.

---
*NCMRWF / MoES Regime-Aware Mixture-of-Experts (RAMP) Project*