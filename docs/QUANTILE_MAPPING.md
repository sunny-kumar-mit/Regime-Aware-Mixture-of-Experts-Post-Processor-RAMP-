# Empirical Quantile Mapping (Baseline 2)

**Project:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Class:** `EmpiricalQuantileMapper` (`ml/baselines/models/quantile_mapping.py`)  
**Version:** `quantile_mapping_v1`  
**Status:** COMPLETE  

---

## 1. Mathematical Formulation

Empirical Quantile Mapping (EQM) aligns the cumulative distribution function (CDF) of the raw NWP forecast to match the empirical CDF of observed rainfall:
$$R_{\text{corrected}} = F_{\text{obs}}^{-1} \left( F_{\text{nwp}}(R_{\text{nwp}}) \right)$$
where $F_{\text{nwp}}$ is the empirical CDF of raw NWP precipitation and $F_{\text{obs}}^{-1}$ is the inverse empirical CDF (quantile function) of observed precipitation.

---

## 2. Precipitation-Aware Dry-Occurrence Handling

Rainfall possesses a high probability mass at zero (dry days). Blindly fitting a continuous CDF across both dry and wet days introduces artificial drizzle biases.

`EmpiricalQuantileMapper` implements a two-component precipitation-aware architecture:
1. **Rain Occurrence Threshold:**  
   $R < 0.1$ mm is classified as dry.
2. **Frequency Matching:**  
   Let $p_{\text{dry, nwp}} = P(R_{\text{nwp}} \le 0.1)$ and $p_{\text{dry, obs}} = P(R_{\text{obs}} \le 0.1)$.
   If the NWP forecast falls below the dry probability threshold ($R_{\text{nwp}} \le 0.1$ mm), the prediction is mapped to $0.0$ mm.
3. **Conditional Wet Distribution:**  
   Quantile mapping is fitted strictly on positive rainfall events ($R > 0.1$ mm) using $K=100$ empirical quantiles.

---

## 3. Tail Extrapolation & Extreme Rainfall Preservation

Empirical quantile functions are bounded by the maximum observed event in the training dataset ($q_{\max}$). When an unprecedented tropical storm or deluge occurs ($R_{\text{nwp}} > q_{\text{nwp, max}}$), standard nearest-neighbor interpolation caps the prediction, destroying extreme weather forecasts.

To prevent this, `EmpiricalQuantileMapper` implements **Linear Tail Extrapolation**:
$$\text{Tail Ratio} = \frac{q_{\text{obs}, 0.99}}{q_{\text{nwp}, 0.99}}$$
$$R_{\text{corrected}} = q_{\text{obs}, \max} + \text{Tail Ratio} \times (R_{\text{nwp}} - q_{\text{nwp}, \max})$$

This policy guarantees:
- Extreme convective precipitation ($>64.5, >115.6, >204.5$ mm) is preserved and dynamically scaled.
- High-intensity tail events are not capped at historical sample maximums.
- $R_{\text{corrected}} \ge 0.0$ is strictly satisfied.
