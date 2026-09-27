# Dataset Card: ramp_dataset_real_v1.0.0 (v1.0.0)

## Overview
Authoritative paired training dataset for RAMP (Regime-Aware Mixture-of-Experts Post-Processor).
- **Organization:** Ministry of Earth Sciences (MoES) / NCMRWF
- **Problem Statement:** SIH26080
- **Operational Data Mode:** `NOT_AVAILABLE`
- **Creation Timestamp:** `2026-09-26T18:09:52.073926+00:00Z`
- **Status:** `NOT_AVAILABLE`

## Data Sources & Provider Hierarchy
1. **PRIMARY:** NCMRWF NCUM Deterministic (0.12°), NCMRWF NEPS Ensemble (0.12°), IMD 0.25° Gridded Rainfall Observations.
2. **SECONDARY:** NCEP GFS (0.25°), GEFS (0.50°) [Classified as PUBLIC_PROXY].
3. **DEMO:** SYNTHETIC_DEMO.

## Spatial & Temporal Specifications
- **Spatial Extent:** India Meteorological Domain (6.5°N–38.5°N, 66.5°E–100.5°E)
- **Canonical RAMP Resolution:** 0.25° (~27 km)
- **Mass-Conservation:** Enforced during 0.12° -> 0.25° regridding.
- **Lead Times:** [6, 12, 18, 24, 48, 72, 96, 120]
- **Temporal Alignment:** `forecast_valid_time == observation_time`

## Target Definitions
- `observed_rainfall_mm`: Continuous rainfall ground truth from IMD
- `rain_label`: >= 0.1 mm/day
- `heavy_label`: >= 64.5 mm/day
- `very_heavy_label`: >= 115.6 mm/day
- `extreme_label`: >= 204.5 mm/day

## Anti-Leakage Guarantee
Strictly audited: NO future observations or post-event accumulated statistics enter predictor set X.
