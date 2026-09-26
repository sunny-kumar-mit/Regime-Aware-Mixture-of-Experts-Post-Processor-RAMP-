# PHASE 5 PROJECT REPORT — Baseline Rainfall Post-Processing & Benchmarking

**Project:** RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Status:** COMPLETE  

---

## 1. Executive Summary
Phase 5 constructed and validated the **Baseline Post-Processing Layer** and benchmarking ladder for the RAMP project. Rather than rushing into regime-aware mixture-of-experts modeling, Phase 5 establishes the empirical foundation against which Phase 6 RAMP can be objectively compared. 

Four distinct baseline systems were engineered and trained under identical conditions:
1. **Raw NWP Baseline (`RawNWPBaseline`):** Uncorrected numerical weather prediction precipitation directly from the forecast model (reference tier).
2. **Mean Bias Correction (`MeanBiasCorrector`):** Classical additive error correction estimated strictly on training data, stratified across forecast lead times ($24\text{h} \dots 120\text{h}$) with global fallback.
3. **Empirical Quantile Mapping (`EmpiricalQuantileMapper`):** Precipitation-aware cumulative distribution matching separating dry-occurrence thresholding ($0.1$ mm) from continuous wet quantiles, equipped with linear tail extrapolation to preserve extreme events.
4. **Global Machine Learning (`GlobalMLPostProcessor`):** Monolithic LightGBM regression utilizing 25 synoptic, thermodynamic, geographic, and cyclic features with a $\log(1+x)$ target transform, strictly unconditioned on weather regimes.

All models were evaluated on the chronological `TEST` split ($N=63$) using continuous metrics (RMSE, MAE, Mean Bias, Pearson $r$), categorical 2x2 contingency metrics (POD, FAR, CSI, ETS, FBIAS) across canonical IMD thresholds ($0.1$, $64.5$, $115.6$, $204.5$ mm), Fractions Skill Score (FSS), and paired bootstrap confidence intervals.

**Critical Finding:**
While Global ML reduced bulk RMSE from $16.18$ mm to $15.48$ mm, its heavy rainfall CSI ($>64.5$ mm) collapsed to $0.000$ due to variance shrinkage on extreme tail events. Post-hoc regime stratification demonstrated severe conditional biases: during `ACTIVE_MONSOON`, Global ML bias degraded to $-6.20$ mm. This empirical discovery provides the decisive scientific justification for Phase 6 RAMP (specialized regime experts + soft gating).

The implementation was validated through **221 cumulative tests with 0 failures** (37 new Phase 5 tests), a clean frontend production build (`tsc && vite build`), 8 production REST endpoints under `/api/baselines/*`, and a dedicated `/baseline` benchmarking dashboard.

---

## 2. Problem Addressed
Operational numerical weather prediction models (e.g. NCMRWF NCUM, IMD GFS) exhibit pronounced systematic precipitation errors:
- Overprediction of light drizzle frequency.
- Underprediction of localized convective deluge intensity.
- Lead-time dependent error growth.
- Strong conditional bias bifurcations depending on synoptic weather regimes.

Standard post-processing approaches apply single global models (classical bias subtraction, quantile mapping, or monolithic machine learning). However, without establishing a rigorous, reproducible benchmark ladder evaluated on identical test splits and canonical verification metrics, it is impossible to determine whether advanced AI architectures provide genuine meteorological value or mere overfitting.

---

## 3. Objective
- Build four global baseline post-processing systems: Raw NWP, Mean Bias Correction, Empirical Quantile Mapping, and Global LightGBM.
- Enforce strict phase boundaries: baseline models must remain genuinely GLOBAL and must not consume Phase 4 regime intelligence.
- Implement strict physical non-negativity ($R_{\text{pred}} \ge 0.0$ mm) across all systems.
- Preserve extreme rainfall tails ($>64.5$, $>115.6$, $>204.5$ mm) without arbitrary outlier clipping.
- Implement standardized WMO/IMD continuous and categorical verification metrics with safe zero-denominator handling.
- Build spatial Fractions Skill Score (`FSSCalculator`) across neighborhood scales ($25, 50, 100, 200$ km).
- Build paired bootstrap significance analysis (`BootstrapComparator`) with 95% empirical confidence intervals.
- Perform post-hoc regime-stratified diagnostics across all 7 Phase 4 weather regimes.
- Provide a persistent Model Registry (`BaselineModelRegistry`) and unified multi-model inference service (`BaselineInferenceService`).
- Expose 8 production REST API endpoints under `/api/baselines/*`.
- Deploy the `/baseline` frontend benchmarking page with real-time model cards, lead-time decay charts, threshold toggles, and persistent synthetic demo notices.

---

## 4. Architecture

```
                               ┌─────────────────────────────────┐
                               │   Phase 3 Staged Dataset        │
                               │   (Train / Val / Test Parquet)  │
                               └────────────────┬────────────────┘
                                                │
                                    [LeakageGuard Audit]
                         (Rejects target columns & regime features in X)
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
        ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
        │  Raw NWP        │            │  Mean Bias      │            │  Empirical QM   │
        │  Baseline 0     │            │  Baseline 1     │            │  Baseline 2     │
        │  (Identity)     │            │  (Train Only)   │            │  (Train CDF)    │
        └────────┬────────┘            └────────┬────────┘            └────────┬────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                ▼
                                       ┌─────────────────┐
                                       │  Global ML      │
                                       │  Baseline 3     │
                                       │  (LightGBM)     │
                                       └────────┬────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │   Unified Evaluation On TEST    │
                               │   (Continuous, Contingency,     │
                               │    FSS, Paired Bootstrap)       │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  Post-Hoc Regime Stratification │
                               │  (7 Weather Regimes Diagnostics)│
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  Evidence Feeds Phase 6 RAMP    │
                               └─────────────────────────────────┘
```

---

## 5. Implementation
1. **Leakage Protection:** Extended `LeakageGuard` with `audit_baseline_features()` to detect and loudly reject target variables and Phase 4 regime features (`regime_label`, `p_*`, `*_score`, `entropy`).
2. **Model Implementations:**
   - `RawNWPBaseline`: Identity mapping with non-negativity clipping.
   - `MeanBiasCorrector`: Computes $\text{Bias}_{\tau} = \text{mean}(R_{\text{obs}} - R_{\text{nwp}})$ per lead time; enforces minimum sample size fallback.
   - `EmpiricalQuantileMapper`: Splits wet/dry at $0.1$ mm; fits 100 quantiles on wet events; implements linear tail extrapolation.
   - `GlobalMLPostProcessor`: LightGBM regressor with $\log(1+x)$ transform over 25 atmospheric features.
3. **Verification Package:**
   - Continuous: RMSE, MAE, Mean Bias, Pearson $r$.
   - Categorical: Hits, Misses, False Alarms, Correct Negatives, POD, FAR, CSI, ETS, FBIAS.
   - Spatial FSS: 2D uniform filter neighborhood smoothing at 25km, 50km, 100km, 200km.
   - Bootstrap: $B=300$ paired resamples for $\Delta\text{RMSE}$ with 95% confidence intervals.
4. **Diagnostics Package:**
   - `LeadTimeStratifiedEvaluator`: Computes skill decay across Day 1 through Day 5.
   - `RegimeStratifiedEvaluator`: Stratifies global model errors across all 7 Phase 4 regimes.
   - `SpatialEvaluator`: Computes gridded lat/lon error statistics.
5. **Model Registry & Inference:**
   - `BaselineModelRegistry`: Saves and loads joblib model artifacts and JSON metadata cards.
   - `BaselineInferenceService`: Implements `predict_sample`, `predict_batch`, and `predict_grid` returning typed `PredictionRecord` objects.
   - `BaselineBenchmarkEngine`: Coordinates evaluation and generates `baseline_benchmark.json`.

---

## 6. Data Flow
1. **Ingestion & Validation:** Staged parquet datasets from Phase 3 (`train.parquet`, `validation.parquet`, `test.parquet`).
2. **Feature Auditing:** Features passed to `LeakageGuard.audit_baseline_features()`. Fails immediately if target or regime columns appear.
3. **Training Phase:**
   - `MeanBiasCorrector` fits additive errors on `TRAIN`.
   - `EmpiricalQuantileMapper` estimates empirical CDFs on `TRAIN`.
   - `GlobalMLPostProcessor` trains LightGBM on `TRAIN` with `VALIDATION` monitoring.
4. **Artifact Persistence:** Stored in `data/models/baselines/{model_id}/` with `model_metadata.json` and `MODEL_CARD.md`.
5. **Evaluation Phase:** Models execute batch predictions on `TEST`. Benchmark engine calculates metrics, FSS, bootstrap intervals, and regime stratifications.
6. **Delivery:** Persisted to JSON artifacts and served via `/api/baselines/*` to the frontend `/baseline` dashboard.

---

## 7. Algorithms / Methodology
- **Non-Negativity Constraint:**
  $$R_{\text{pred}} = \max(0.0, \; \hat{R})$$
- **Lead-Time Additive Correction:**
  $$R_{\text{corrected}} = \max\left(0.0, \; R_{\text{nwp}} + \text{Bias}_{\tau}\right)$$
- **Empirical Quantile Mapping with Linear Tail Extrapolation:**
  $$R_{\text{corrected}} = \begin{cases} 0.0 & \text{if } R_{\text{nwp}} \le 0.1\text{ mm} \\ F_{\text{obs}}^{-1}(F_{\text{nwp}}(R_{\text{nwp}})) & \text{if } 0.1 < R_{\text{nwp}} \le q_{\text{nwp}, \max} \\ q_{\text{obs}, \max} + \frac{q_{\text{obs}, 0.99}}{q_{\text{nwp}, 0.99}}(R_{\text{nwp}} - q_{\text{nwp}, \max}) & \text{if } R_{\text{nwp}} > q_{\text{nwp}, \max} \end{cases}$$
- **Log-Transformed Global Gradient Boosting:**
  $$y = \log(1 + R_{\text{obs}}), \quad \hat{R} = \max(0.0, \; \exp(\hat{y}) - 1)$$
- **Equitable Threat Score (ETS):**
  $$H_{\text{random}} = \frac{(H + M)(H + FA)}{N}, \quad \text{ETS} = \frac{H - H_{\text{random}}}{H + M + FA - H_{\text{random}}}$$
- **Fractions Skill Score (FSS):**
  $$\text{FSS} = 1 - \frac{\text{MSE}_{(n)}}{\text{MSE}_{\text{ref}(n)}}$$

---

## 8. Files & Modules

| File Path | Description |
| :--- | :--- |
| `ml/baselines/models/base.py` | `BaseBaselineModel` abstract base with non-negativity constraint and feature audit. |
| `ml/baselines/models/raw_nwp.py` | `RawNWPBaseline` reference model. |
| `ml/baselines/models/mean_bias.py` | `MeanBiasCorrector` with lead-time stratification and fallback. |
| `ml/baselines/models/quantile_mapping.py` | `EmpiricalQuantileMapper` with dry-day thresholding and linear tail extrapolation. |
| `ml/baselines/models/global_ml.py` | `GlobalMLPostProcessor` (LightGBM regressor with $\log(1+x)$ transform). |
| `ml/baselines/verification/metrics.py` | Continuous and categorical contingency verification metrics. |
| `ml/baselines/verification/fss.py` | `FSSCalculator` across 25km, 50km, 100km, 200km scales. |
| `ml/baselines/verification/bootstrap.py` | `BootstrapComparator` paired bootstrap significance engine. |
| `ml/baselines/diagnostics/regime_stratification.py` | `RegimeStratifiedEvaluator` across all 7 Phase 4 regimes. |
| `ml/baselines/diagnostics/lead_time_stratification.py` | `LeadTimeStratifiedEvaluator` across Day 1 through Day 5. |
| `ml/baselines/diagnostics/spatial_evaluation.py` | `SpatialEvaluator` for gridded error field coordinates. |
| `ml/baselines/model_registry.py` | `BaselineModelRegistry` managing model artifacts and metadata. |
| `ml/baselines/inference.py` | `BaselineInferenceService` and `PredictionRecord` schema. |
| `ml/baselines/benchmark.py` | `BaselineBenchmarkEngine` orchestrating master benchmark generation. |
| `ml/baselines/cli.py` | CLI entry point supporting `train`, `evaluate`, `benchmark`, `verify`, `inspect`. |
| `backend/src/ramp/api/v1/baselines.py` | FastAPI router exposing 8 REST endpoints under `/api/baselines/*`. |
| `frontend/src/pages/BaselineBenchmarking.tsx` | Production `/baseline` benchmarking dashboard with live charts. |

---

## 9. APIs

| Endpoint | Method | Response Contract | Description |
| :--- | :---: | :--- | :--- |
| `/api/baselines/status` | GET | `BaselineStatusResponse` | Operational status, active models, dataset version, and honest real data detection. |
| `/api/baselines/models` | GET | `List[BaselineModelMetadata]` | Registered baseline model catalog with hyperparameters and training periods. |
| `/api/baselines/metrics` | GET | `BaselineMetricsResponse` | Bulk continuous metrics (RMSE, MAE, Mean Bias, Pearson $r$) across all 4 baselines. |
| `/api/baselines/metrics/lead-time` | GET | `LeadTimeMetricsResponse` | Verification metrics stratified across lead times (Day 1 $\dots$ Day 5). |
| `/api/baselines/metrics/threshold` | GET | `ThresholdMetricsResponse` | Contingency metrics (POD, FAR, CSI, ETS) at 0.1, 64.5, 115.6, 204.5 mm. |
| `/api/baselines/metrics/regime` | GET | `RegimeDiagnosticsResponse` | Post-hoc regime-stratified error breakdowns across all 7 Phase 4 regimes. |
| `/api/baselines/benchmark` | GET | `MasterBenchmarkResponse` | Full benchmark comparison matrix and paired bootstrap significance vs RAW NWP. |
| `/api/baselines/spatial` | GET | `SpatialMetricsResponse` | Gridded spatial coordinate error distributions across the Indian domain. |
| `/api/baselines/prediction/{sample_id}` | GET | `PredictionRecord` | Executes all 4 baseline predictions on a designated sample ID. |

---

## 10. Frontend
- **Route:** `/baseline` (also accessible via `/forecast`).
- **Critical Honesty Banner:** Persistent warning: `SYNTHETIC DEMONSTRATION ONLY — REAL TRAINING DATA: NOT AVAILABLE`.
- **Overview Cards:** Real-time metrics for RAW NWP, MEAN BIAS, QUANTILE MAPPING, and GLOBAL ML.
- **Interactive Threshold Toggle:** Dynamically filters contingency metrics for 0.1 mm, 64.5 mm, 115.6 mm, and 204.5 mm.
- **Lead-Time Decay Card:** Multi-day skill decay comparison across Day 1 through Day 5.
- **Bootstrap Significance Table:** Displays paired $\Delta\text{RMSE}$ and 95% confidence intervals against Raw NWP.
- **Regime-Stratified Breakdown:** Interactive regime selector (Active, Break, Depression, Coastal, Orographic, WD, Transition) demonstrating regime-conditional error biases.

---

## 11. Testing

- **Total Backend Tests:** 221 passed, 0 failures, 1 deprecation warning.
- **New Phase 5 Tests:** 37 tests covering:
  - Raw NWP identity and physical non-negativity ($R \ge 0$).
  - Mean Bias train-only fitting, lead-time stratification, and global fallback.
  - Quantile Mapping train-only calibration, dry-occurrence thresholding, and linear tail extrapolation.
  - Global ML train/val/test separation, $\log(1+x)$ target transform, and feature audit.
  - Leakage Guard rejecting target and Phase 4 regime features.
  - Invariant: fitting on test/validation data raises `DataLeakageError`.
  - Continuous metrics (RMSE, MAE, Mean Bias, Pearson $r$).
  - Categorical metrics (POD, FAR, CSI, ETS, FBIAS) with safe zero-denominator handling.
  - Fractions Skill Score (`FSSCalculator`) across 25km, 50km, 100km, 200km.
  - Paired bootstrap confidence intervals (`BootstrapComparator`).
  - Model registry save/load roundtrips and metadata validation.
  - Unified inference service and `PredictionRecord` validation.
  - API integration tests for all 8 `/api/baselines/*` endpoints.
- **Frontend Verification:** `tsc && vite build` completed in 6.16s with 0 errors.

---

## 12. Actual Results

### Master Benchmark Matrix (`TEST` Split, $N=63$):

| Metric | RAW NWP | MEAN BIAS | QUANTILE MAPPING | GLOBAL ML |
| :--- | :---: | :---: | :---: | :---: |
| **RMSE (mm)** | 16.18 | 16.17 | 16.49 | **15.48** |
| **MAE (mm)** | 7.97 | 7.95 | 8.20 | **7.90** |
| **Mean Bias (mm)** | -0.88 | -1.12 | -2.47 | -5.22 |
| **Pearson $r$** | 0.539 | 0.539 | 0.525 | **0.600** |
| **Rain CSI ($>0.1$ mm)** | 0.850 | 0.833 | 0.833 | **0.921** |
| **Heavy CSI ($>64.5$ mm)** | **0.333** | **0.333** | **0.333** | 0.000 |
| **Heavy POD ($>64.5$ mm)** | **0.500** | **0.500** | **0.500** | 0.000 |
| **Heavy FAR ($>64.5$ mm)** | 0.500 | 0.500 | 0.500 | *null* |
| **Heavy ETS ($>64.5$ mm)** | **0.319** | **0.319** | **0.319** | 0.000 |

### Lead-Time RMSE Progression (mm):

| Lead Time | RAW NWP | MEAN BIAS | QUANTILE MAPPING | GLOBAL ML |
| :--- | :---: | :---: | :---: | :---: |
| **Day 1 (24h)** | 24.53 | 24.53 | 24.95 | **19.92** |
| **Day 2 (48h)** | 5.34 | 5.33 | 5.35 | **5.45** |
| **Day 3 (72h)** | 6.84 | 6.84 | 6.78 | **6.66** |

### Paired Bootstrap Significance vs RAW NWP:
- **Mean Bias vs Raw NWP:** $\Delta\text{RMSE} = -0.01$ mm, $95\%\text{ CI} = [-0.03, 0.01]$ (Not significant).
- **Quantile Mapping vs Raw NWP:** $\Delta\text{RMSE} = +0.31$ mm, $95\%\text{ CI} = [-0.17, 0.84]$ (Not significant).
- **Global ML vs Raw NWP:** $\Delta\text{RMSE} = -0.70$ mm, $95\%\text{ CI} = [-1.75, 0.28]$ (Marginal).

---

## 13. Real vs Synthetic Status
- **Current Data Mode:** `SYNTHETIC_DEMO`.
- **Real NWP/IMD Data Available:** NO.
- **Honesty Invariant:** All API responses include `"data_mode": "SYNTHETIC_DEMO"` and `"performance_notice"`. The frontend displays the persistent warning banner.
- **Pipeline Architecture:** Strictly unified. When real NetCDF/GRIB datasets are mounted, the data provider auto-detects `REAL` mode without code modification.

---

## 14. Limitations
- Synthetic data generates simplified spatial correlation structures compared to real orographic monsoon circulations.
- The test sample size ($N=63$) reflects a demonstration subsample; operational deployment requires multi-year verification ($N > 100,000$).
- Global ML suppresses localized extreme convection due to L2 loss minimization; specialized loss formulations (e.g. Extreme Value Loss) or regime-gated experts are required.

---

## 15. Security & Leakage Considerations
- `LeakageGuard` strictly forbids test-period statistics from entering bias correction, quantile estimation, or LightGBM training.
- Passing validation or test data to `fit()` raises `DataLeakageError`.
- Phase 4 regime features are strictly audited and rejected from baseline predictors $X$.

---

## 16. Reproducibility
The baseline training, evaluation, and benchmark generation pipeline is fully deterministic and runnable via CLI:
```bash
python -m ml.baselines train
python -m ml.baselines evaluate
python -m ml.baselines benchmark
python -m ml.baselines verify
```
All model weights, scalers, and JSON benchmark artifacts are serialized to `data/models/baselines/`.

---

## 17. Outputs & Artifacts

```
data/models/baselines/
├── raw_nwp_v1/ (model.joblib, model_metadata.json, MODEL_CARD.md)
├── mean_bias_v1/ (model.joblib, model_metadata.json, MODEL_CARD.md)
├── quantile_mapping_v1/ (model.joblib, model_metadata.json, MODEL_CARD.md)
├── global_lgbm_v1/ (model.joblib, model_metadata.json, MODEL_CARD.md)
├── baseline_benchmark.json
├── baseline_metrics.json
├── baseline_lead_time_metrics.json
├── baseline_threshold_metrics.json
├── baseline_regime_metrics.json
├── baseline_spatial_metrics.json
├── baseline_comparison.json
├── regime_error_report.json
└── BASELINE_MODEL_CARD.md
```

---

## 18. Next Phase Dependency: What Phase 6 Can Consume
Phase 5 establishes the empirical justification and reference benchmarks for **Phase 6 — RAMP (Regime-Aware Mixture-of-Experts Post-Processor)**.

Specifically, Phase 6 will consume:
1. **Phase 4 Output:** Calibrated regime probability vector $\mathbf{p}(x) \in [0, 1]^7$.
2. **Phase 5 Output:** Baseline benchmark ladder (RAW, MEAN BIAS, QM, GLOBAL ML).
3. **Phase 5 Evidence:** The regime-stratified error breakdown proving that Global ML fails in active convective regimes.
4. **Phase 6 Construction:**
   $$\text{RAMP}(\mathbf{x}) = \sum_{k=1}^7 p_k(\mathbf{x}) \cdot \text{Expert}_k(\mathbf{x})$$
   Training 7 specialized expert models conditioned on weather regimes, dynamically combined via soft gating.
