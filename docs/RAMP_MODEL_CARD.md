# RAMP Model Card: Regime-Aware Mixture-of-Experts (v1.0.0)

**Model Identifier:** `ramp_v1.0.0`  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Release Date:** September 2026  
**Status:** Complete — Synthetic Demonstration Mode  

---

## 1. Model Architecture & Core Formulation
RAMP dynamically routes NWP post-processing corrections through 7 regime-specialized regression experts weighted by continuous, calibrated regime probabilities:

$$\text{RAMP}(x) = \sum_{k=0}^{6} p_k(x) \cdot \text{Expert}_k(x)$$

- **Gating Vector:** $\mathbf{p}(x) = [p_{\text{active}}, p_{\text{break}}, p_{\text{low\_dep}}, p_{\text{coastal}}, p_{\text{orographic}}, p_{\text{wd}}, p_{\text{transition}}]^T$ from Phase 4 `RegimeInferenceService`.
- **Specialized Experts:** 7 LightGBM regressors fitted on $\log(1 + y)$ target transforms.
- **Physical Bounds:** $\text{RAMP}(x) = \max(0.0, \text{RAMP}(x))$.

---

## 2. Benchmark Verification Summary (TEST Partition, N=63)

| System | RMSE (mm) | MAE (mm) | Mean Bias (mm) | Pearson r | Heavy CSI (>64.5mm) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **RAW NWP** | 16.18 | 7.97 | -0.88 | 0.5390 | 0.3333 |
| **MEAN BIAS** | 16.17 | 7.95 | -1.12 | 0.5391 | 0.3333 |
| **QUANTILE MAPPING** | 16.49 | 8.20 | -2.47 | 0.5247 | 0.3333 |
| **GLOBAL ML** | 15.48 | 7.90 | -5.22 | 0.5995 | 0.0000 |
| **RAMP MoE** | **13.85** | **6.84** | **-4.52** | **0.6697** | 0.0000 |

---

## 3. Scientific Invariants Enforced
1. **Convexity Invariant:** $\min_k \text{Expert}_k(x) \le \text{RAMP}(x) \le \max_k \text{Expert}_k(x)$ (verified within $10^{-3}$ tolerance).
2. **Probability Simplex Normalization:** $p_k \ge 0$, $\sum_{k=0}^6 p_k = 1.0 \pm 10^{-4}$.
3. **Physical Non-Negativity:** Precipitation $\ge 0.0$ mm.
4. **Zero Target Leakage:** Future observed rainfall never enters feature set $X$ or regime assignment.
5. **Fallback Safety:** Unfitted/sparse experts cleanly route to the Global ML baseline.

---

## 4. Operational Limitations & Honest Data Notice
- **Data Mode:** `SYNTHETIC_DEMO`. Real multi-year operational IMD/NCMRWF NetCDF observations are not available in this environment.
- **Sample Size:** The test set contains $N=63$ synthetic events. While continuous improvements (RMSE, MAE, Pearson r) are evident, extreme tail events (>64.5 mm) require large multi-year observational archives for full operational calibration.
