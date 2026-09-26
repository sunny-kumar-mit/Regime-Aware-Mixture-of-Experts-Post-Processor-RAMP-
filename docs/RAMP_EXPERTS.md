# RAMP Specialized Regime Experts

**SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts**  
**Ministry of Earth Sciences (MoES) | National Centre for Medium Range Weather Forecasting (NCMRWF)**

---

## 1. Meteorological Rationale for Seven Regime Experts

The Indian summer monsoon system is characterized by distinct synoptic forcing mechanisms that induce divergent NWP error dynamics. A single global correction function $f(x)$ typically minimizes bulk root-mean-square error by shrinking forecast extremes toward climatological means. To resolve localized error structures without sacrificing calibration, RAMP trains seven specialized regression experts:

| Regime ID | Canonical Name | Meteorological Driving Mechanism | NWP Error Bias Pattern |
|:---|:---|:---|:---|
| **0** | `ACTIVE_MONSOON` | Strong cross-equatorial monsoon flow, active trough | Severe underestimation of convective bursts (-6.2 mm bias in Global ML) |
| **1** | `BREAK_MONSOON` | Northward shift of trough toward Himalayan foothills | False alarms in central peninsula; drizzle overestimation |
| **2** | `LOW_DEPRESSION` | Low pressure areas & depressions formed in Bay of Bengal | Spatial displacement of core precipitation swath |
| **3** | `COASTAL` | West coast Arabian Sea moisture convergence & sea-breeze | Underestimation of diurnal coastal precipitation peaks |
| **4** | `OROGRAPHIC` | Western Ghats & Northeast elevation barrier uplift | Excessive rain-shadow drizzle; localized peak suppression |
| **5** | `WESTERN_DISTURBANCE` | Extratropical upper-level troughs across northwest India | Timing offsets; misrepresentation of winter/pre-monsoon storms |
| **6** | `TRANSITION_OTHER` | Onset/withdrawal stages or mixed synoptic states | Multi-modal error variance during atmospheric restructuring |

---

## 2. Base Expert Architecture & Target Transformation

Every regime expert inherits from the base `RegimeExpert` interface:

```python
class RegimeExpert:
    regime: WeatherRegime
    feature_columns: List[str]
    use_log1p_target: bool = True
    min_samples_to_train: int = 5
    model_backend: LGBMRegressor
```

### Target Transformation Contract
Rainfall distributions are zero-inflated and heavily right-skewed. To stabilize variance and prevent extreme outliers from dominating gradients:

1. **Forward Transform (Training):**
   $$y_{\text{train}} = \log(1 + \max(0.0, R_{\text{obs}}))$$
2. **Inverse Transform (Inference):**
   $$\hat{R}_{\text{mm}} = \exp(\hat{y}) - 1$$
3. **Physical Constraint Enforcement:**
   $$\hat{R}_{\text{final}} = \max(0.0, \hat{R}_{\text{mm}})$$

---

## 3. Training-Time Regime Assignment

To avoid **target leakage**, experts are never partitioned using observed future rainfall or post-hoc ground-truth regime classifications. Instead, training samples are partitioned using **forecast-time Phase 4 regime inference**:

$$\text{inferred\_regime}_i = \arg\max_{k \in \{0..6\}} p_k(x_i)$$

Each sample $x_i$ is routed to the corresponding expert $\text{Expert}_k$. At inference time, **all seven experts produce predictions simultaneously**, and the soft gating engine combines them.

---

## 4. Minimum Sample Requirement & Fallback Hierarchy

In demonstration or sparse datasets, certain rare regimes may exhibit insufficient training events. To maintain numerical stability:

$$\text{MIN\_EXPERT\_SAMPLES} = 5$$

If $N_{\text{train}} < 5$:
- The expert is marked: `status = INSUFFICIENT_DATA`, `is_fitted = False`.
- During inference, requests to this expert route automatically through the **Phase 5 Global ML baseline** (`global_lgbm_v1`).
- The prediction record transparently logs:
  ```json
  {
    "fallback_used": true,
    "expert_sources": {
      "COASTAL": "GLOBAL_ML_FALLBACK",
      "OROGRAPHIC": "GLOBAL_ML_FALLBACK"
    }
  }
  ```
