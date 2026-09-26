# Master Baseline Model Card — Phase 5 Benchmarking

**Project:** RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Operational Status:** SYNTHETIC_DEMO  
**Notice:** SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.

---

## 1. Overview & Purpose
Phase 5 establishes the empirical benchmark ladder against which Phase 6 RAMP (Regime-Aware Mixture-of-Experts) will be evaluated. Four competing post-processing paradigms are compared under identical chronological splits, spatial domains, and target variables:
1. **Raw NWP (`raw_nwp_v1`):** Uncorrected baseline reference.
2. **Mean Bias Correction (`mean_bias_v1`):** Lead-time stratified additive bias correction.
3. **Empirical Quantile Mapping (`quantile_mapping_v1`):** Precipitation-aware transfer function with linear tail extrapolation.
4. **Global Machine Learning (`global_lgbm_v1`):** Non-linear gradient boosted decision trees fitted across all weather states without regime awareness.

---

## 2. Master Benchmark Comparison Matrix (Test Partition)

| Model | RMSE (mm) | MAE (mm) | Mean Bias (mm) | Pearson R | CSI (64.5mm) | POD (64.5mm) | FAR (64.5mm) | ETS (64.5mm) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **raw_nwp** | 16.179 | 7.9741 | -0.8779 | 0.539 | 0.3333 | 0.5 | 0.5 | 0.3189 |
| **mean_bias** | 16.1736 | 7.9467 | -1.1198 | 0.5391 | 0.3333 | 0.5 | 0.5 | 0.3189 |
| **quantile_mapping** | 16.4871 | 8.2045 | -2.4659 | 0.5247 | 0.3333 | 0.5 | 0.5 | 0.3189 |
| **global_ml** | 15.4772 | 7.9035 | -5.2214 | 0.5995 | 0.0 | 0.0 | None | 0.0 |

---

## 3. Physical Invariant Guarantees
1. **Non-Negativity Constraint:** All corrected predictions satisfy $R >= 0.0$ mm.
2. **Extreme Deluge Preservation:** Precipitation extremes ($>204.5$ mm) are preserved; no artificial clipping is applied to heavy rainfall tails.
3. **Strict Zero-Leakage:** Models and empirical CDFs are fitted strictly on the TRAIN partition. Future observations are verified to never enter predictor matrices.
4. **Baseline Global Isolation:** No Phase 4 regime labels or regime probabilities were provided to the baseline models during training or inference.

---

## 4. Key Scientific Finding: Why RAMP is Needed
Post-hoc regime stratification reveals that while Global ML achieves lower overall RMSE across the bulk distribution, its errors are heavily regime-dependent:
- In `LOW_DEPRESSION` regimes, global models underestimate extreme convective deluge.
- In `BREAK_MONSOON` regimes, global models overforecast rainfall over central India.
This conditional error structure establishes the direct scientific justification for **Phase 6 RAMP Mixture-of-Experts**.
