# RAMP Architecture Specification: Regime-Aware Mixture-of-Experts

**SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts**  
**Ministry of Earth Sciences (MoES) | National Centre for Medium Range Weather Forecasting (NCMRWF)**

---

## 1. System Overview & Defining Formulation

The defining architectural formulation of RAMP is a continuous, soft-gated Mixture-of-Experts (MoE) rainfall post-processor:

$$\text{RAMP}(x) = \sum_{k=0}^{6} p_k(x) \cdot \text{Expert}_k(x)$$

where:
- $p_k(x)$ is the calibrated, forecast-time probability that the current synoptic state belongs to canonical meteorological regime $k \in \{0, \dots, 6\}$, computed by the frozen **Phase 4 Weather Regime Intelligence Engine**.
- $\text{Expert}_k(x)$ is a specialized regression model trained specifically to resolve the precipitation error dynamics characteristic of regime $k$, taking physical NWP predictors from **Phase 3**.

```
                   PHASE 3 NWP PREDICTORS (X)
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
       RAINFALL FEATURES             PHASE 4 REGIME ENGINE
               │                               │
               │                               ▼
               │                    Calibrated P(regime | x)
               │                               │
               │                        [p0, p1, ..., p6]
               │                               │
               ▼                               ▼
     ┌───────────────────┐             SOFT GATING
     │  7 REGIME EXPERTS │                     │
     │                   │                     │
     │ Expert 0 ACTIVE   │◄────────────────────┤
     │ Expert 1 BREAK    │◄────────────────────┤
     │ Expert 2 LOW/DEP  │◄────────────────────┤
     │ Expert 3 COASTAL  │◄────────────────────┤
     │ Expert 4 OROGRAPH │◄────────────────────┤
     │ Expert 5 WD       │◄────────────────────┤
     │ Expert 6 TRANSIT  │◄────────────────────┘
     └─────────┬─────────┘
               │
      Expert Predictions E_k(x)
               │
               ▼
      WEIGHTED COMBINATION: Σ p_k(x) · E_k(x)
               │
               ▼
        RAMP PREDICTION
               │
               ▼
     PHYSICAL POST-PROCESSING: max(0.0, R_RAMP)
               │
               ▼
      VERIFICATION ENGINE (Phase 5 Benchmark Reference)
```

---

## 2. Core Invariants & Mathematical Guarantees

1. **Strictly Soft Gating (No Hard Switching):**  
   Hard switching (`if regime == ACTIVE: use Expert 1`) is forbidden. Atmospheric transitions across the subcontinent exhibit continuous gradient dynamics. Soft gating ensures smooth spatial and temporal transitions without boundary discontinuities.

2. **Probability Simplex Normalization:**  
   $$p_k(x) \ge 0 \quad \forall k, \qquad \sum_{k=0}^{6} p_k(x) = 1.0 \pm 10^{-4}$$
   Any malformed or unnormalized gating vector causes immediate loud failure.

3. **Mathematical Convexity Invariant:**  
   Because $p_k \ge 0$ and $\sum p_k = 1$, the combined prediction must lie strictly within the convex hull of the expert outputs:
   $$\min_{k \in \{0..6\}} \text{Expert}_k(x) \le \text{RAMP}(x) \le \max_{k \in \{0..6\}} \text{Expert}_k(x)$$

4. **Physical Non-Negativity:**  
   $$\text{RAMP}_{\text{final}}(x) = \max(0.0, \text{RAMP}(x))$$
   Precipitation rate cannot be negative. Tail events (e.g. 204.5+ mm) are not artificially capped.

5. **Fallback Hierarchy:**  
   $$\text{Specialized Regime Expert} \xrightarrow[\text{if unavailable}]{\text{fallback}} \text{Phase 5 Global ML Baseline} \xrightarrow[\text{if unavailable}]{\text{fallback}} \text{Raw NWP}$$
   Every prediction audits and logs `fallback_used` and `expert_sources` explicitly.

6. **Zero Target Leakage:**  
   Observed future rainfall is never used to determine training or inference regime assignments. Gating vectors originate solely from forecast-time meteorological features.

---

## 3. Interaction with Preceding Phases

- **Phase 3 (Predictors & Dataset):** Supplies canonical physical predictors (wind components, mslp, vorticity, humidity, cyclic seasonal features) without target leakage.
- **Phase 4 (Regime Engine):** Supplies frozen, calibrated multi-class regime probabilities $p_k(x)$ via `RegimeInferenceService`.
- **Phase 5 (Frozen Benchmarking):** Frozen baseline ladder (RAW NWP, MEAN BIAS, QUANTILE MAPPING, GLOBAL ML) serves as the immutable reference against which RAMP is benchmarked.
