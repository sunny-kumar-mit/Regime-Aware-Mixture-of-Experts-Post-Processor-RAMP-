# Baseline Rainfall Post-Processing & Benchmarking

**Project:** RAMP — Regime-Aware Mixture-of-Experts Post-Processor  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Phase:** 5 — Baseline Post-Processing & Benchmarking  
**Status:** COMPLETE (SYNTHETIC_DEMO)  

---

## 1. Overview & Scientific Purpose

Phase 5 establishes the **Baseline Post-Processing Layer** and benchmarking ladder for the RAMP project. Prior to building specialized regime-specific experts and soft mixture-of-experts gating (scheduled for Phase 6), the project requires rigorous, reproducible, and standardized benchmarks.

The objective is to evaluate four baseline systems against ground-truth targets under identical conditions:
1. **Baseline 0 — Raw NWP (`RawNWPBaseline`):** Uncorrected numerical weather prediction precipitation directly from the forecast model. Primary benchmark against which all correction skill is measured.
2. **Baseline 1 — Mean Bias Correction (`MeanBiasCorrector`):** Classical additive bias correction estimated strictly on training data, stratified by lead-time horizon with global fallback.
3. **Baseline 2 — Empirical Quantile Mapping (`EmpiricalQuantileMapper`):** Precipitation-aware distribution matching separating dry-occurrence thresholding ($0.1$ mm) from positive continuous rainfall, equipped with linear tail extrapolation.
4. **Baseline 3 — Global Machine Learning (`GlobalMLPostProcessor`):** Monolithic LightGBM regressor with $\log(1+x)$ target transform, utilizing all Phase 3 atmospheric predictor features while strictly excluding regime labels or regime probabilities.

---

## 2. Benchmark Ladder & Core Scientific Question

For any spatial grid cell and forecast horizon $t$:
- Raw NWP Rainfall: $R_{\text{nwp}}$
- Observed Ground Truth: $R_{\text{obs}}$
- Corrected Forecast: $R_{\text{pred}} = f(R_{\text{nwp}}, \mathbf{x}_{\text{nwp}})$

```
   Raw NWP (Baseline 0)
        │
        ▼
   Mean Bias Correction (Baseline 1)
        │
        ▼
   Empirical Quantile Mapping (Baseline 2)
        │
        ▼
   Global Machine Learning (Baseline 3)
        │
        ▼
   [Regime-Stratified Benchmark Diagnostics]
   "Where do global methods conditionally fail by weather regime?"
        │
        ▼
   Phase 6: RAMP (Regime-Aware Mixture-of-Experts)
```

### Strict Phase Boundary
- Baseline models are **strictly GLOBAL** (trained across all weather states).
- Baseline models **do not consume** Phase 4 regime labels, probabilities, or confidence scores.
- Phase 4 regime intelligence is applied **post-hoc** as a diagnostic evaluator to analyze conditional error structures.

---

## 3. Standardized Evaluation Protocol

To ensure 100% scientific fairness, all four baselines are evaluated against identical:
- **Temporal Splitting:** Chronological train/validation/test partitions with embargo periods preventing serial leakage.
- **Spatial Grid:** Canonical $0.25^\circ \times 0.25^\circ$ Indian subcontinent bounding domain ($6.5^\circ\text{N} - 38.5^\circ\text{N}, 66.5^\circ\text{E} - 100.5^\circ\text{E}$).
- **Lead Times:** Daily accumulations for Day 1 ($24\text{h}$) through Day 5 ($120\text{h}$).
- **Event Thresholds:** Canonical IMD thresholds ($0.1$ mm rain occurrence, $64.5$ mm heavy, $115.6$ mm very heavy, $204.5$ mm extremely heavy).
- **Physical Invariants:** Strict physical non-negativity constraint ($R \ge 0.0$ mm) enforced across all systems.

---

## 4. Module Architecture

```
ml/baselines/
├── __init__.py
├── __main__.py
├── cli.py                        # CLI: train, evaluate, benchmark, verify, inspect
├── model_registry.py             # BaselineModelRegistry & BaselineModelMetadata
├── inference.py                  # BaselineInferenceService & PredictionRecord schema
├── benchmark.py                  # BaselineBenchmarkEngine (master matrix + bootstrap)
├── models/
│   ├── __init__.py
│   ├── base.py                   # BaseBaselineModel (non-negativity & leakage check)
│   ├── raw_nwp.py                # RawNWPBaseline
│   ├── mean_bias.py              # MeanBiasCorrector (lead-time bias + fallback)
│   ├── quantile_mapping.py       # EmpiricalQuantileMapper (dry-day + linear tail)
│   └── global_ml.py              # GlobalMLPostProcessor (LightGBM + log1p)
├── verification/
│   ├── __init__.py
│   ├── metrics.py                # Continuous (RMSE, MAE, Bias, r) & Categorical (POD, FAR, CSI, ETS)
│   ├── fss.py                    # FSSCalculator (25km, 50km, 100km, 200km)
│   └── bootstrap.py              # BootstrapComparator (paired differences & 95% CIs)
└── diagnostics/
    ├── __init__.py
    ├── regime_stratification.py  # RegimeStratifiedEvaluator (7 Phase 4 regimes)
    ├── lead_time_stratification.py # LeadTimeStratifiedEvaluator (Day 1..5)
    └── spatial_evaluation.py     # SpatialEvaluator (gridded coordinate errors)
```
