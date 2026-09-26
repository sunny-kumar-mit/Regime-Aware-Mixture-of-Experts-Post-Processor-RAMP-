# Model Card: quantile_mapping_v1

## Overview
- **Model Type:** QUANTILE_MAPPING
- **Version:** v1.0.0
- **Dataset Version:** v0.3.0
- **Created At:** 2026-09-26T02:44:43.322791
- **Operational Data Mode:** SYNTHETIC_DEMO

## Purpose & Scope
Serves as a global benchmark in the RAMP SIH26080 baseline evaluation ladder.
Trained across all weather states without regime-specific conditioning.

## Verification Metrics
```json
{
  "rmse": 16.4871,
  "mae": 8.2045,
  "mean_bias": -2.4659,
  "pearson_r": 0.5247,
  "sample_count": 63
}
```

## Physical Invariant Guarantees
- Continuous rainfall predictions constrained to R >= 0.0 mm.
- Extreme precipitation tails preserved without artificial clipping.
- Zero data leakage: fitted strictly on TRAIN data without future observation inputs.
