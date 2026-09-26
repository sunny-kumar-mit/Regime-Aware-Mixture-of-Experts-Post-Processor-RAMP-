# RAMP Dataset Card: ramp_dataset_v0.3.0

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Dataset Version:** `0.3.0`  
**Generated At:** `2026-09-25T21:06:55.094104`  
**Operational Data Mode:** `SYNTHETIC_DEMO`  

---

## 1. Executive Summary & Scientific Purpose

The **RAMP Training Dataset** couples high-resolution Numerical Weather Prediction (NWP) forecast states (GFS/GEFS/NCMRWF) with ground-truth observation targets (IMD 0.25° gridded rainfall) for machine-learned post-processing.

This dataset is strictly designed to serve:
- **Phase 4:** Weather Regime Identification & Classifier
- **Phase 5:** Baseline ML Post-Processing Models (LightGBM, Quantile Mapping)
- **Phase 6:** Regime-Aware Mixture-of-Experts (RAMP MoE)
- **Phase 7:** Extreme Rainfall Probability Engine

---

## 2. Dataset Dimensions & Coverage

- **Total Samples:** 360
- **Feature Predictors ($X$):** 27
- **Target Variables ($Y$):** 6
- **Spatial Domain:** India Canonical Grid (0.25° × 0.25°)
- **Bounding Box:** {'lat_min': 21.0, 'lat_max': 21.5, 'lon_min': 78.0, 'lon_max': 78.5}
- **Time Range:** 2025-07-02T00:00:00+00:00 to 2025-07-22T00:00:00+00:00
- **Integrity Checksum (SHA-256):** `Pending generation`

---

## 3. Canonical Target Definitions

| Target Column | Type | Definition & Threshold | Source Standard |
| :--- | :--- | :--- | :--- |
| `observed_rainfall_mm` | Continuous | 24-hour accumulated rainfall (mm) | IMD 0.25° Gridded Daily Obs |
| `rainfall_occurrence` | Binary | Event >= 0.1 mm / 24h (0 = dry/trace, 1 = rain) | IMD Measurable Rain Standard |
| `heavy_rainfall` | Binary | Event >= 64.5 mm / 24h | IMD Heavy Rainfall Criterion |
| `very_heavy_rainfall` | Binary | Event >= 115.6 mm / 24h | IMD Very Heavy Rainfall Criterion |
| `extremely_heavy_rainfall` | Binary | Event >= 204.5 mm / 24h | IMD Extremely Heavy Rainfall Criterion |
| `rainfall_anomaly` | Continuous | Observed minus train-fitted climatology baseline | Fitted on TRAIN only |

*Note: Regime labels (`regime_label`, `regime_label_source`, `regime_label_confidence`) are deliberately initialized to `None` in Phase 3 to prevent premature classification before Phase 4.*

---

## 4. Chronological Split Breakdown

| Partition | Row Count | Start Time | End Time | Purge Buffer |
| :--- | :--- | :--- | :--- | :--- |
| **TRAIN** | 243 | 2025-07-02T00:00:00+00:00 | 2025-07-15T00:00:00+00:00 | N/A |
| **VALIDATION** | 54 | 2025-07-16T00:00:00+00:00 | 2025-07-18T00:00:00+00:00 | 24 hours |
| **TEST** | 63 | 2025-07-19T00:00:00+00:00 | 2025-07-22T00:00:00+00:00 | 24 hours |

*Zero Random Splitting: Partitions are strictly chronological with temporal embargo buffers to eliminate autocorrelation leakage.*

---

## 5. Statistical Distribution & Class Imbalance

### TRAIN Partition
- **Rainfall Mean / Median:** 9.80 mm / 4.66 mm
- **Rainfall Quantiles (P90 / P95 / P99 / Max):** 24.7 mm / 35.8 mm / 79.5 mm / 135.0 mm
- **Heavy Rainfall Events (>= 64.5mm):** 6 (2.4690%)
- **Very Heavy Rainfall Events (>= 115.6mm):** 2 (0.8230%)
- **Extremely Heavy Rainfall Events (>= 204.5mm):** 0 (0.0000%)

### VALIDATION Partition
- **Rainfall Mean / Median:** 19.39 mm / 4.16 mm
- **Rainfall Quantiles (P90 / P95 / P99 / Max):** 57.9 mm / 64.5 mm / 225.0 mm / 225.0 mm
- **Heavy Rainfall Events (>= 64.5mm):** 4 (7.4070%)
- **Very Heavy Rainfall Events (>= 115.6mm):** 2 (3.7040%)
- **Extremely Heavy Rainfall Events (>= 204.5mm):** 2 (3.7040%)

### TEST Partition
- **Rainfall Mean / Median:** 12.07 mm / 4.39 mm
- **Rainfall Quantiles (P90 / P95 / P99 / Max):** 35.1 mm / 42.0 mm / 85.8 mm / 85.8 mm
- **Heavy Rainfall Events (>= 64.5mm):** 2 (3.1750%)
- **Very Heavy Rainfall Events (>= 115.6mm):** 0 (0.0000%)
- **Extremely Heavy Rainfall Events (>= 204.5mm):** 0 (0.0000%)

---

## 6. Scientific Invariants & Leakage Verification

- [x] **No Target Leakage:** Verified that observation columns and forecast errors are absent from predictor set $X$.
- [x] **Temporal Causality:** Forecast valid time $T_{valid} = T_{init} + 	ext{lead}$. Observations strictly matched on $T_{valid}$.
- [x] **Zero Test Contamination:** Climatology, missing value imputations, and feature normalizations are fitted strictly on `TRAIN`.
- [x] **Extreme Rainfall Preservation:** Rainfall exceeding 204.5 mm (and up to 400+ mm) is preserved without artificial outlier truncation.
- [x] **Honest Data Provenance:** Marked as `SYNTHETIC_DEMO` when real IMD archives are not yet staged.
