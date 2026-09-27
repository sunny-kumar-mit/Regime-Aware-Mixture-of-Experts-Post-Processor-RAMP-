# MODEL CARD: ramp_moe_v2.0.0

## 1. Model Overview
- **Model Identifier:** `ramp_moe_v2.0.0`
- **Model Type:** `REGIME_AWARE_MOE`
- **Lifecycle Status:** `DEVELOPMENT`
- **Data Mode:** `SYNTHETIC_DEMO`
- **Dataset Version:** `ramp_dataset_real_v1.0.0`
- **Feature Schema Version:** `ramp_features_v1.0.0`
- **Target Schema Version:** `ramp_targets_v1.0.0`
- **Model SHA-256 Checksum:** `bf8aaf917323d02d0669ade81c44d4a165df9ea92d814eef1e45e25fddba105e`

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
  "mae": 9.8919,
  "rmse": 16.9975,
  "bias": 4.8628,
  "correlation": 0.8622,
  "r2": 0.7186
}
```

## 5. Known Limitations & Scientific Honesty Notice
Trained in `SYNTHETIC_DEMO` mode. **WARNING:** Because authoritative NCMRWF/IMD training datasets are not mounted in this environment, this model artifact is strictly classified as DEVELOPMENT and must NOT be used for real operational forecasting.

---
*NCMRWF / MoES Regime-Aware Mixture-of-Experts (RAMP) Project*