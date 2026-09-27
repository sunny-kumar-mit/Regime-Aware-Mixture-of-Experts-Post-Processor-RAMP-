# MODEL CARD: ramp_global_v2.0.0

## 1. Model Overview
- **Model Identifier:** `ramp_global_v2.0.0`
- **Model Type:** `GLOBAL_ML`
- **Lifecycle Status:** `DEVELOPMENT`
- **Data Mode:** `SYNTHETIC_DEMO`
- **Dataset Version:** `ramp_dataset_real_v1.0.0`
- **Feature Schema Version:** `ramp_features_v1.0.0`
- **Target Schema Version:** `ramp_targets_v1.0.0`
- **Model SHA-256 Checksum:** `632981bbfaeb9e9579e4ad7493171691dd058047f0cb7f6242eab4301708cf71`

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
  "mae": 10.5942,
  "rmse": 18.8118,
  "bias": 5.3506,
  "correlation": 0.8357,
  "r2": 0.6553
}
```

## 5. Known Limitations & Scientific Honesty Notice
Trained in `SYNTHETIC_DEMO` mode. **WARNING:** Because authoritative NCMRWF/IMD training datasets are not mounted in this environment, this model artifact is strictly classified as DEVELOPMENT and must NOT be used for real operational forecasting.

---
*NCMRWF / MoES Regime-Aware Mixture-of-Experts (RAMP) Project*