# MODEL CARD — RAMP
## Regime-Aware Mixture-of-Experts Post-Processor
**SIH26080 | NCMRWF / Ministry of Earth Sciences**  
**Model Card Version:** 1.0.0  
**Date:** 2026-09-25

---

## Model Details

| Field | Value |
|-------|-------|
| **Model name** | RAMP (Regime-Aware Mixture-of-Experts Post-Processor) |
| **Version** | 1.0.0 |
| **Type** | Post-processing system (not a primary NWP model) |
| **Task** | Bias correction of gridded NWP rainfall forecasts |
| **Input** | NWP forecast bundle + static terrain features |
| **Output** | Corrected rainfall (mm/24h) + regime probabilities + extreme rainfall probabilities |
| **Organisations** | NCMRWF / Ministry of Earth Sciences |
| **Problem Statement** | SIH26080 |

---

## System Description

RAMP is a **two-stage** AI post-processor:

### Stage 1 — Regime Classifier
- **Architecture:** LightGBM gradient-boosted ensemble with isotonic probability calibration
- **Input:** 23 atmospheric + physics + terrain features (see DATA_CONTRACTS.md §3)
- **Output:** 7-dimensional **soft probability vector** over weather regimes
- **Constraint:** Probabilities always sum to 1.0 (enforced via softmax + validator)
- **No hard class is ever returned** — the system is inherently probabilistic

### Stage 2 — Soft Mixture-of-Experts (RAMP Core)
- **7 regime-specific correction experts** (one per regime)
- Each expert: LightGBM model trained on regime-stratified data subsets
- **Blending:** Probabilistic weighted sum — `corrected = Σ p_regime × Expert_regime(NWP)`
- Expert architecture: Input = NWP features + regime probability context (30 features total)
- Optional upgrade: PyTorch neural expert for complex regime interactions

### Stage 3 — Extreme Rainfall Probability Engine
- Logistic regression + isotonic calibration per threshold
- Inputs: RAMP corrected rainfall + regime probabilities + NWP ensemble spread
- Thresholds: 64.5, 115.6, 204.5 mm/24h (IMD operational thresholds)

---

## Weather Regimes

| ID | Name | Definition |
|----|------|-----------|
| 0 | Active Monsoon | Vigorous cross-equatorial flow, widespread organised rainfall |
| 1 | Break Monsoon | Monsoon trough shifts north, dry peninsula, rainfall at Himalayan foothills/coasts |
| 2 | Monsoon Low/Depression | Organised low-pressure system (LP/D/DD/CS) influencing rainfall |
| 3 | Coastal Rainfall | Sea-breeze-driven or onshore-flow-driven coastal rainfall |
| 4 | Orographic Rainfall | Terrain-forced uplift (Western Ghats, Northeast, Himalayan foothills) |
| 5 | Western Disturbance | Extra-tropical disturbance from the west; pre/post-monsoon |
| 6 | Transition/Other | Mixed or undefined — absorbs unclassifiable days |

---

## Baseline Models (for verification comparison)

| Model | Description |
|-------|-------------|
| `raw_nwp` | Raw NWP output — no correction applied |
| `mean_bias` | Additive global mean-bias correction (long-term climatological offset) |
| `qmap` | Quantile mapping — distributional correction using historical CDF |
| `global_ml` | Single global LightGBM correction (regime-unaware baseline) |
| `ramp` | **RAMP** — this system |

---

## Verification Metrics

| Metric | Type | Formula | Notes |
|--------|------|---------|-------|
| RMSE | Continuous | sqrt(mean((fcst-obs)²)) | Lower is better |
| CSI | Categorical | H/(H+M+F) | Higher is better [0,1] |
| POD | Categorical | H/(H+M) | Higher is better [0,1] |
| FAR | Categorical | F/(H+F) | Lower is better [0,1] |
| ETS | Categorical | (H-Hr)/(H+M+F-Hr) | Higher is better [-1/3, 1] |
| FSS | Spatial | 1 - MSE_f/MSE_ref | Higher is better [0,1] |

Where: H=Hits, M=Misses, F=False Alarms, Hr=random hits

---

## Training Data Requirements

> **Note:** RAMP is currently in pre-training phase. No training data has been ingested.
> All current outputs are in SYNTHETIC_DEMO mode.

| Data Source | Variables | Period Required | Resolution |
|-------------|-----------|-----------------|------------|
| NCMRWF NCUM historical | Precipitation + dynamic fields | >= 5 years | 0.17° / 6h |
| IMD Gridded Rainfall | Daily rainfall observation | >= 5 years | 0.25° / daily |
| ERA5 (optional) | PWAT, CAPE, vorticity, OLR | >= 5 years | 0.25° / 6h |
| SRTM30 DEM | Terrain elevation | Static | 1 km |
| India district shapefiles | ADM2 boundaries | Static | Vector |

**Minimum recommended training period:** June–September (JJAS monsoon season) × 5 years  
**Regime label source:** Manual/automatic labelling from NCMRWF archives or ERA5 clustering

---

## Training Procedure

### Regime Classifier Training
1. Compute 23-feature vectors for all training grid points × times
2. Label each sample with dominant regime (from NCMRWF/ERA5 analysis)
3. Train LightGBM classifier with class weights proportional to regime frequency
4. Apply isotonic calibration on held-out validation set
5. Verify: calibration curve, Brier score, log-loss per regime
6. Log all metrics + model artifacts to MLflow

### Expert Training
1. Stratify training data by dominant regime label (from classifier)
2. For each of 7 regimes, train LightGBM corrector on that stratum
3. Use 5-fold cross-validation (time-blocked, no leakage)
4. Log hyperparameters, RMSE per regime to MLflow

### RAMP Blending (no additional training)
- Blending weights come directly from the regime classifier output
- No additional parameters to train — the blending gate is analytical

---

## Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| Requires NWP dynamic fields (u850, v850, etc.) | Cannot run on precipitation-only NWP | Provide fallback climatological features |
| Regime classifier trained on historical patterns | May underperform for unprecedented events | Transition regime absorbs novel patterns |
| District aggregation loses sub-district spatial detail | Coarser district-level uncertainty | Grid product is always available |
| No real-time ensemble spread ingested | P(extreme) calibration is less sharp | NEPS adapter planned for ensemble spread |
| Demo mode uses synthetic data | Verification scores are not operationally valid | Clear labelling, warning banners |

---

## Scientific Integrity Statement

1. RAMP **does not** generate primary weather forecasts. It **post-processes** existing NWP output.
2. Verification scores reported by this system are **only valid against real IMD observations**.
3. In SYNTHETIC_DEMO mode, all scores are labelled with `data_mode=SYNTHETIC_DEMO`.
4. **No verification scores or model accuracy figures are fabricated or hard-coded.**
5. Regime probabilities are **always** a 7-class soft distribution summing to 1.0.
6. The IMD operational rainfall thresholds (64.5, 115.6, 204.5 mm/24h) are used exactly as defined.

---

## Intended Use

| Use Case | Supported |
|----------|-----------|
| Post-processing NCMRWF NCUM/NEPS forecasts | Yes |
| Post-processing NOAA GFS/GEFS forecasts | Yes |
| Generating district-level rainfall advisories | Yes |
| Operational heavy rainfall warning support | Yes (with real data and calibrated models) |
| Replacing primary NWP forecast | **No** |
| Generating forecasts without any NWP input | **No** |
| Climate projections | **No** — short-range (1-5 day) NWP only |

---

## Out-of-Scope Uses

- Long-range seasonal forecasting
- Cyclone track prediction
- Air quality or temperature forecasting
- Replacing human meteorologist judgment

---

## Ethical Considerations

- RAMP outputs must be reviewed by trained meteorologists before being used for public warnings.
- Errors in heavy rainfall forecasts can have life-safety implications.
- The system must **always** communicate uncertainty through probabilistic outputs.
- Demo mode must **never** be used in an operational warning context.

---

## Citation (Placeholder)

```
RAMP: Regime-Aware Mixture-of-Experts Post-Processor for Monsoon Rainfall Forecasts
SIH26080, NCMRWF / Ministry of Earth Sciences, 2026.
```
