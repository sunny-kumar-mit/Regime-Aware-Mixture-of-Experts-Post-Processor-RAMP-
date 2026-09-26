# RAMP Inference Service Specification

**SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts**  
**Ministry of Earth Sciences (MoES) | National Centre for Medium Range Weather Forecasting (NCMRWF)**

---

## 1. Unified Inference Pipeline

The `RAMPInferenceService` coordinates the complete operational post-processing workflow without manual intervention:

```
[Forecast Predictors X]
        │
        ├─────────────────────────────────────────────────┐
        │                                                 │
        ▼                                                 ▼
Phase 4 Regime Inference                         Phase 6 7-Expert Pool
- Calculate indicators                           - E_0(x) ACTIVE
- Calibrated P(regime | X)                       - E_1(x) BREAK
- Shannon Entropy & Uncertainty                  - E_2(x) LOW_DEP
        │                                        - E_3(x) COASTAL (or Fallback)
        ▼                                        - E_4(x) OROGRAPHIC (or Fallback)
GateWeights [p0, ..., p6]                        - E_5(x) WD (or Fallback)
        │                                        - E_6(x) TRANSITION
        │                                                 │
        └───────────────────────┬─────────────────────────┘
                                │
                                ▼
                    Soft Combination Engine
                    RAMP(x) = Σ p_k(x) · E_k(x)
                                │
                                ▼
                    Physical Invariant Guard
                    - Check Convexity: min(E_k) <= RAMP <= max(E_k)
                    - Non-negativity: max(0.0, RAMP)
                                │
                                ▼
                    RAMPPredictionRecord
```

---

## 2. API & Python Methods

### 1. `predict_sample(row: Dict[str, Any] | pd.Series) -> RAMPPredictionRecord`
Generates end-to-end post-processed forecast for a single station or grid point, returning complete explainable decomposition:

```json
{
  "sample_id": "beb63898945bcbe3",
  "forecast_valid_time": "2025-07-19 00:00:00+00:00",
  "latitude": 21.0,
  "longitude": 78.5,
  "lead_time_hours": 24,
  "raw_nwp_prediction": 1.10,
  "global_ml_prediction": 3.21,
  "ramp_prediction": 4.59,
  "gate_probabilities": {
    "ACTIVE_MONSOON": 1.0,
    "BREAK_MONSOON": 0.0,
    "LOW_DEPRESSION": 0.0,
    "COASTAL": 0.0,
    "OROGRAPHIC": 0.0,
    "WESTERN_DISTURBANCE": 0.0,
    "TRANSITION_OTHER": 0.0
  },
  "expert_predictions": {
    "ACTIVE_MONSOON": 4.59,
    "BREAK_MONSOON": 0.14,
    "LOW_DEPRESSION": 2.24,
    "COASTAL": 3.21,
    "OROGRAPHIC": 3.21,
    "WESTERN_DISTURBANCE": 3.21,
    "TRANSITION_OTHER": 4.68
  },
  "weighted_contributions": {
    "ACTIVE_MONSOON": 4.59,
    "BREAK_MONSOON": 0.0,
    "LOW_DEPRESSION": 0.0,
    "COASTAL": 0.0,
    "OROGRAPHIC": 0.0,
    "WESTERN_DISTURBANCE": 0.0,
    "TRANSITION_OTHER": 0.0
  },
  "top_regime": "ACTIVE_MONSOON",
  "top_probability": 1.0,
  "entropy": 0.0,
  "uncertainty": "LOW",
  "transition_state": "STABLE",
  "fallback_used": true,
  "data_mode": "SYNTHETIC_DEMO",
  "model_version": "ramp_v1.0.0"
}
```

### 2. `predict_batch(df: pd.DataFrame) -> pd.DataFrame`
Performs vectorized prediction across large datasets with aligned gating probability matrices.

### 3. `predict_grid(grid_df: pd.DataFrame) -> Dict[str, Any]`
Computes 2D spatially continuous post-processed fields across latitude/longitude coordinates for frontend geospatial visualization.
