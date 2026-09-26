# Model Card: raw_nwp_v1

## Overview
- **Model Type:** RAW_NWP
- **Version:** v1.0.0
- **Dataset Version:** v0.3.0
- **Created At:** 2026-09-26T02:44:43.316584
- **Operational Data Mode:** SYNTHETIC_DEMO

## Purpose & Scope
Serves as a global benchmark in the RAMP SIH26080 baseline evaluation ladder.
Trained across all weather states without regime-specific conditioning.

## Verification Metrics
```json
{
  "rmse": 16.179,
  "mae": 7.9741,
  "mean_bias": -0.8779,
  "pearson_r": 0.539,
  "sample_count": 63
}
```

## Physical Invariant Guarantees
- Continuous rainfall predictions constrained to R >= 0.0 mm.
- Extreme precipitation tails preserved without artificial clipping.
- Zero data leakage: fitted strictly on TRAIN data without future observation inputs.
