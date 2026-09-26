# RAMP Model Card: Regime-Aware Mixture-of-Experts Post-Processor

**Model ID:** `ramp_v1.0.0`  
**Dataset Version:** `v0.3.0`  
**Data Mode:** `SYNTHETIC_DEMO`  
**Evaluation Notice:** `SYNTHETIC DEMONSTRATION ONLY — Real training data is not available.`  

---

## 1. Model Overview
RAMP (Regime-Aware Mixture-of-Experts Post-Processor) dynamically routes weather forecast corrections through 7 regime-specialized regression experts weighted by continuous, calibrated regime probabilities:
$$\text{RAMP}(x) = \sum_{k=0}^6 p_k(x) \cdot \text{Expert}_k(x)$$

## 2. Benchmark Summary (TEST Partition, N=63)
- **RAW NWP RMSE:** 16.18 mm
- **Global ML RMSE:** 15.48 mm
- **RAMP (MoE) RMSE:** 13.85 mm
- **Heavy Rain CSI (>64.5mm):** RAW=0.3333, Global ML=0.0, RAMP=0.0

## 3. Scientific Invariants
1. $p_k \ge 0, \sum p_k = 1.0$ (calibrated soft gating).
2. Physical non-negativity: $R \ge 0.0$ mm.
3. Mathematical convexity: $\min_k E_k \le \text{RAMP} \le \max_k E_k$.
4. Zero target leakage: future rainfall never enters feature set X or regime assignment.
