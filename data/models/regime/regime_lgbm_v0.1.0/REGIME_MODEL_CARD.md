# RAMP Model Card: regime_lgbm_v0.1.0

**Model Architecture:** LightGBM Multi-Class Classifier + Isotonic Calibration  
**Model Version:** `0.1.0`  
**Dataset Version:** `0.3.0`  
**Operational Mode:** `SYNTHETIC_DEMO` (Real Training Data Not Available)  
**Calibration Fitted Split:** `VALIDATION` (Zero Test Set Contamination)  

---

## 1. Intended Use
Provides probabilistic weather regime classification across 7 canonical monsoon regimes.
Feeds directly into Phase 6 (RAMP Mixture-of-Experts) soft blending gates.

---

## 2. Test Set Performance (Held-out Chronological Test Partition)

> ⚠️ **SYNTHETIC DEMONSTRATION NOTICE**  
> Metrics below are computed on synthetic demonstration data. They validate pipeline integrity, probabilistic calibration, and soft gating mechanics. They MUST NOT be cited as real-world atmospheric accuracy.

| Metric | Score | Description |
| :--- | :--- | :--- |
| **Accuracy** | 0.9206 | Overall top-1 classification accuracy |
| **Balanced Accuracy** | 0.6950 | Unweighted mean of recall per class |
| **Macro F1** | 0.5922 | Unweighted harmonic mean of precision and recall |
| **Weighted F1** | 0.9268 | Support-weighted F1 across all classes |
| **Brier Score (Calibrated)** | 0.1568 | Mean squared probability error (Lower is better) |
| **Log Loss (Calibrated)** | 1.4013 | Cross-entropy loss on held-out test data |

---

## 3. Regime-Wise Performance

| Regime | Precision | Recall | F1-Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| `ACTIVE_MONSOON` | 0.980 | 0.980 | 0.980 | 50 |
| `BREAK_MONSOON` | 0.333 | 1.000 | 0.500 | 1 |
| `LOW_DEPRESSION` | 1.000 | 0.800 | 0.889 | 10 |
| `COASTAL` | 0.000 | 0.000 | 0.000 | 0 |
| `OROGRAPHIC` | 0.000 | 0.000 | 0.000 | 0 |
| `WESTERN_DISTURBANCE` | 0.000 | 0.000 | 0.000 | 0 |
| `TRANSITION_OTHER` | 0.000 | 0.000 | 0.000 | 2 |

---

## 4. Probabilistic Uncertainty & Entropy
Model posteriors provide Shannon entropy:
$$H(p) = -\sum_{i=1}^7 p_i \log_2(p_i)$$
Normalized entropy $H_{\text{norm}} \in [0, 1]$ categorizes model state into `LOW`, `MEDIUM`, or `HIGH` uncertainty.
