# Baseline Verification & Meteorological Metrics

**Project:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Package:** `ml/baselines/verification/`  
**Status:** COMPLETE  

---

## 1. Overview

Meteorological verification of quantitative precipitation forecasts requires multi-tiered evaluation: continuous error measures, categorical 2x2 contingency table skill scores across warning thresholds, neighborhood spatial verification (FSS), and paired bootstrap confidence intervals.

---

## 2. Continuous Verification Metrics

For predictions $\hat{y}_i$ and observations $y_i$ over $N$ samples:

1. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)^2}$$
2. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\hat{y}_i - y_i|$$
3. **Mean Bias:**
   $$\text{Bias} = \frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)$$
4. **Pearson Correlation Coefficient ($r$):**
   $$r = \frac{\sum (\hat{y}_i - \bar{\hat{y}})(y_i - \bar{y})}{\sqrt{\sum (\hat{y}_i - \bar{\hat{y}})^2 \sum (y_i - \bar{y})^2}}$$

---

## 3. Categorical Contingency Metrics

For a given precipitation threshold $T \in \{0.1, 64.5, 115.6, 204.5\}$ mm:

| Event Contingency | Observed $\ge T$ | Observed $< T$ |
| :--- | :---: | :---: |
| **Forecast $\ge T$** | Hits ($H$) | False Alarms ($FA$) |
| **Forecast $< T$** | Misses ($M$) | Correct Negatives ($CN$) |

### Metric Formulations:
1. **Probability of Detection (POD) / Hit Rate:**
   $$\text{POD} = \frac{H}{H + M} \quad (\text{Range: } [0, 1], \; \text{Optimal: } 1)$$
   *Safe Handling:* Returns `None` if $H + M = 0$.

2. **False Alarm Ratio (FAR):**
   $$\text{FAR} = \frac{FA}{H + FA} \quad (\text{Range: } [0, 1], \; \text{Optimal: } 0)$$
   *Safe Handling:* Returns `None` if $H + FA = 0$.

3. **Critical Success Index (CSI) / Threat Score:**
   $$\text{CSI} = \frac{H}{H + M + FA} \quad (\text{Range: } [0, 1], \; \text{Optimal: } 1)$$
   *Safe Handling:* Returns `None` if $H + M + FA = 0$.

4. **Equitable Threat Score (ETS) / Gilbert Skill Score:**
   Corrects for hits expected purely by random chance:
   $$H_{\text{random}} = \frac{(H + M)(H + FA)}{N}$$
   $$\text{ETS} = \frac{H - H_{\text{random}}}{H + M + FA - H_{\text{random}}} \quad (\text{Range: } [-1/3, 1], \; \text{No Skill: } 0)$$

5. **Frequency Bias (FBIAS):**
   $$\text{FBIAS} = \frac{H + FA}{H + M}$$

---

## 4. Fractions Skill Score (FSS)

Implemented in `FSSCalculator` (`ml/baselines/verification/fss.py`) based on Roberts and Lean (2008):
$$\text{FSS} = 1 - \frac{\text{MSE}_{(n)}}{\text{MSE}_{\text{ref}(n)}}$$
where $\text{MSE}_{(n)} = \frac{1}{N_x N_y} \sum [P_{(n)}(x,y) - O_{(n)}(x,y)]^2$, evaluated across neighborhood scales:
- **25 km:** $1 \times 1$ grid box
- **50 km:** $3 \times 3$ grid box
- **100 km:** $5 \times 5$ grid box
- **200 km:** $9 \times 9$ grid box

---

## 5. Statistical Significance & Paired Bootstrap

Implemented in `BootstrapComparator` (`ml/baselines/verification/bootstrap.py`):
- $B = 300$ paired resamples with replacement.
- Computes distribution of $\Delta\text{RMSE} = \text{RMSE}_{\text{baseline}} - \text{RMSE}_{\text{raw}}$.
- Constructs empirical 95% bootstrap confidence intervals $[\text{CI}_{0.025}, \text{CI}_{0.975}]$.
- A baseline improvement is declared statistically significant ($p < 0.05$) only if zero lies outside the confidence interval.
