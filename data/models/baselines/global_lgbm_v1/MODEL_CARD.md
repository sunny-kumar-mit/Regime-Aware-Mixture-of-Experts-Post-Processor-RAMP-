# Model Card: global_lgbm_v1

## Overview
- **Model Type:** GLOBAL_LIGHTGBM
- **Version:** v1.0.0
- **Dataset Version:** v0.3.0
- **Created At:** 2026-09-26T02:44:43.325828
- **Operational Data Mode:** SYNTHETIC_DEMO

## Purpose & Scope
Serves as a global benchmark in the RAMP SIH26080 baseline evaluation ladder.
Trained across all weather states without regime-specific conditioning.

## Verification Metrics
```json
{
  "rmse": 15.4772,
  "mae": 7.9035,
  "mean_bias": -5.2214,
  "pearson_r": 0.5995,
  "sample_count": 63
}
```

## Physical Invariant Guarantees
- Continuous rainfall predictions constrained to R >= 0.0 mm.
- Extreme precipitation tails preserved without artificial clipping.
- Zero data leakage: fitted strictly on TRAIN data without future observation inputs.
