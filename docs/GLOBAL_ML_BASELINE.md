# Global Machine Learning Baseline (Baseline 3)

**Project:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Class:** `GlobalMLPostProcessor` (`ml/baselines/models/global_ml.py`)  
**Version:** `global_lgbm_v1`  
**Status:** COMPLETE  

---

## 1. Overview & Objective

Baseline 3 represents a modern, state-of-the-art **Global Machine Learning Post-Processor** using LightGBM Gradient Boosted Decision Trees (GBDT).

In accordance with strict Phase 5 boundaries:
- The model is **strictly GLOBAL** (trained across all weather regimes).
- The model **never consumes** Phase 4 regime labels, regime probabilities, or regime indicators in feature set $X$.
- This model answers the benchmark question: *"What is the maximum skill achievable by a standard unconditioned gradient boosted regressor?"*

---

## 2. Atmospheric Predictor Features

The model uses 25 synoptic and spatial predictors from Phase 3:
1. **NWP Direct & Spatial:** `raw_nwp_rainfall`, `lead_time_hours`, `rainfall_mean_3x3`, `rainfall_max_3x3`, `rainfall_std_3x3`.
2. **Kinematic & Thermodynamic:** `u850`, `v850`, `wind_speed_850`, `wind_direction_850`, `mslp`, `mslp_anomaly`, `temperature`, `relative_humidity`, `precipitable_water`, `cape`, `geopotential_height`.
3. **Geographic & Topographic:** `latitude`, `longitude`, `elevation`, `distance_to_coast`.
4. **Temporal & Seasonal:** `monsoon`, `winter`, `pre_monsoon`, `post_monsoon`, `day_of_year_sin`, `day_of_year_cos`, `valid_hour_sin`, `valid_hour_cos`.

### Forbidden Features (Audited by LeakageGuard):
- Target variables: `observed_rainfall_mm`, `rainfall_occurrence`, `heavy_rainfall`, `very_heavy_rainfall`, `extremely_heavy_rainfall`, `forecast_error`.
- Regime features: `regime_label`, `p_*`, `entropy`, `*_score`.

---

## 3. Skewness Transformation: $\log(1+x)$

Daily rainfall distributions are severely zero-inflated and right-skewed. Optimizing mean squared error directly on raw millimeter targets biases tree split selection towards bulk light-rain samples while producing unstable gradients on extreme tail deluges.

The model implements a target transformation:
$$y_{\text{train}} = \log(1 + R_{\text{obs}})$$

At inference:
$$\hat{R} = \max\left(0.0, \; \exp(\hat{y}) - 1\right)$$

---

## 4. Hyperparameters & Training Configuration

- `n_estimators`: 100
- `learning_rate`: 0.05
- `max_depth`: 6
- `random_state`: 42
- `objective`: Regression (L2 / MSE on log-space)
- Model fitted strictly on `TRAIN`. Validation split used for early monitoring. Test split evaluated post-hoc.
