# Mean Bias Correction (Baseline 1)

**Project:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Class:** `MeanBiasCorrector` (`ml/baselines/models/mean_bias.py`)  
**Version:** `mean_bias_v1`  
**Status:** COMPLETE  

---

## 1. Mathematical Formulation

Classical Mean Bias Correction assumes an additive systematic error in the numerical weather prediction (NWP) model:
$$\text{Bias} = \mathbb{E}[R_{\text{obs}} - R_{\text{nwp}}]$$

The corrected prediction is formulated as:
$$R_{\text{corrected}} = \max\left(0.0, \; R_{\text{nwp}} + \text{Bias}_{\tau}\right)$$
where $\tau$ is the forecast lead time (hours), and $\max(0.0, \cdot)$ enforces the physical non-negativity constraint of rainfall precipitation.

---

## 2. Lead-Time Stratification & Fallback Logic

Forecast bias varies as NWP model skill decays with lead time. `MeanBiasCorrector` fits lead-time specific biases:
$$\text{Bias}_{\tau} = \frac{1}{N_{\tau}} \sum_{i=1}^{N_{\tau}} (R_{\text{obs}, i}^{(\tau)} - R_{\text{nwp}, i}^{(\tau)})$$

### Robust Sample Fallback:
If a given lead time $\tau$ contains fewer than `min_samples_per_lead` (default: 10 samples) in the training dataset, or if an unseen lead time is evaluated during inference:
1. The corrector falls back to the global training bias:
   $$\text{Bias}_{\text{global}} = \frac{1}{N} \sum_{i=1}^{N} (R_{\text{obs}, i} - R_{\text{nwp}, i})$$
2. The fallback invocation is recorded in the model's metadata provenance.

---

## 3. Training & Leakage Invariants

1. **Strict Train-Only Fitting:**  
   The bias calculation is executed strictly on the `TRAIN` chronological split. Attempting to fit on `VALIDATION` or `TEST` data raises `DataLeakageError` immediately.
2. **Physical Non-Negativity:**  
   If $R_{\text{nwp}} + \text{Bias}_{\tau} < 0$, the output is clipped to $0.0$ mm.
3. **No Extreme Capping:**  
   Extreme observations ($>64.5$ mm, $>115.6$ mm, $>204.5$ mm) are preserved; no arbitrary upper thresholds are enforced.
