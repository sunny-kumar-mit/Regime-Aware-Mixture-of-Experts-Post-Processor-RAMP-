# PHASE 3 PROJECT REPORT — Training Dataset & Feature Engineering

**Project:** RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Status:** COMPLETE  

---

## 1. Executive Summary
Phase 3 designed, engineered, and validated the canonical training dataset pipeline for RAMP. It created a feature store of 31 registered meteorological features (27 tabular predictors currently active), 6 canonical verification targets (continuous rainfall, log-transformed precipitation, rain occurrence, and IMD heavy/very heavy/extremely heavy thresholds), strict chronological train/validation/test partitioning with multi-day purge buffers, a zero-tolerance `LeakageGuard`, dataset versioning (`ramp_dataset_v0.3.0`), and Parquet output serialization. The pipeline was verified with 65 dedicated unit and integration tests (bringing the cumulative total to 143 passed tests).

## 2. Problem Addressed
Standard machine learning pipelines for weather forecasting suffer from severe data leakage, including random train/test shuffling across autocorrelated time horizons, future observation inclusion in feature vectors, and uncalibrated unit scales. Phase 3 enforced strict temporal integrity and mathematical boundaries before any model fitting.

## 3. Objective
- Implement a canonical feature registry with typed metadata (`FeatureSpec`).
- Build feature extraction routines: raw NWP rainfall, spatial aggregates (mean, max, std), thermodynamic variables (CAPE, PW, RH, T2M), circulation variables (u850, v850, wind speed, wind direction, MSLP anomaly), and cyclic temporal encodings (day-of-year, seasonal flags).
- Construct 6 canonical targets aligned with IMD meteorological classifications:
  - `observed_rainfall_mm` (continuous $\ge 0$)
  - `log_observed_rainfall` ($\log(1 + y)$)
  - `rain_flag` ($y \ge 0.1$ mm)
  - `heavy_rainfall` ($y \ge 64.5$ mm)
  - `very_heavy_rainfall` ($y \ge 115.6$ mm)
  - `extremely_heavy_rainfall` ($y \ge 204.5$ mm)
- Build chronological data splitters with temporal purge buffers.
- Enforce strict leakage protection via `LeakageGuard`.

## 4. Architecture
```
  Regridded NWP Grids (0.25°)        IMD 0.25° Gridded Observations
              │                                    │
              ▼                                    ▼
    Feature Engineering Engine             Target Extraction Engine
   (27 Active Predictor Features)         (6 Canonical Target Variables)
              │                                    │
              └─────────────────┬──────────────────┘
                                ▼
                       Merged Dataset Matrix
                                │
                                ▼
                 Temporal Splitter + Purge Buffer
                  (TRAIN -> PURGE -> VAL -> TEST)
                                │
                                ▼
                          LeakageGuard
               (Audits X against Future Targets)
                                │
                                ▼
                   Dataset Versioning Engine
                 (data/processed/.../*.parquet)
```

## 5. Implementation
- **Feature Registry (`ml.feature_registry`):** Central catalog defining name, description, physical units, data type, and domain requirements.
- **Dataset Builder (`ml.dataset.builder`):** `RAMPDatasetBuilder` orchestrating the join of predictor grids and observation fields across forecast cycles.
- **Leakage Guard (`ml.dataset.leakage_guard`):** Pre-training validator raising `DataLeakageError` if target columns or future observation fields are detected in predictor matrices.
- **Temporal Splitter (`ml.dataset.temporal_split`):** Chronological partitioner creating Train, Validation, and Test subsets with a 48-hour purge window to eliminate autoregressive contamination.
- **Dataset Versioning (`ml.dataset.versioning`):** Serializes datasets into Parquet format with embedded SHA-256 metadata (`dataset_version.json`).

## 6. Data Flow
1. Harmonized NWP fields and observational arrays from Phase 2 are matched on valid forecast timestamps and spatial coordinates.
2. Predictor features are derived (spatial statistics, wind velocity conversions, MSLP anomalies, cyclical day-of-year sine/cosine).
3. Ground-truth target columns are computed and verified against physical non-negativity.
4. `LeakageGuard` audits the feature set.
5. The dataset is partitioned chronologically into `train.parquet`, `val.parquet`, and `test.parquet`.
6. Dataset version metadata and distribution summaries are exported to `data/processed/training/ramp_dataset_v0.3.0/`.

## 7. Algorithms / Methodology
- **Cyclic Calendar Encoding:**
  $$\text{doy\_sin} = \sin\left(\frac{2\pi \cdot \text{day\_of\_year}}{365.25}\right), \quad \text{doy\_cos} = \cos\left(\frac{2\pi \cdot \text{day\_of\_year}}{365.25}\right)$$
- **Wind Speed and Direction:**
  $$\text{wspd} = \sqrt{u_{850}^2 + v_{850}^2}, \quad \text{wdir} = \left(270 - \text{atan2}(v_{850}, u_{850}) \times \frac{180}{\pi}\right) \pmod{360}$$
- **Purge Buffer:** A 2-day gap between temporal partitions to prevent synoptic-scale auto-correlation leakage across train and validation windows.

## 8. Files & Modules
- `ml/feature_registry.py`: Registry of all 31 feature specifications.
- `ml/dataset/builder.py`: Feature and target extraction orchestrator.
- `ml/dataset/leakage_guard.py`: Leakage detection and verification guard.
- `ml/dataset/temporal_split.py`: Chronological splitters and purge buffers.
- `ml/dataset/versioning.py`: Dataset metadata and serialization.
- `backend/src/ramp/api/v1/datasets.py`: REST endpoints for feature schemas and dataset versions.
- `docs/FEATURE_REGISTRY.md`, `docs/TARGET_DEFINITIONS.md`, `docs/DATA_LEAKAGE.md`: Technical documentation.

## 9. APIs
- `GET /api/datasets/training`: Lists available dataset versions and real data availability.
- `GET /api/datasets/features`: Catalog of registered feature specifications.
- `GET /api/datasets/statistics`: Summary statistics across train, validation, and test partitions.

## 10. Frontend
- Data feeds and dataset management interface displaying feature counts, targets, partition sample sizes, and temporal split boundaries.

## 11. Testing
- 65 unit and integration tests:
  - `backend/tests/unit/dataset/test_dataset_builder.py`
  - `backend/tests/unit/dataset/test_feature_engineering.py`
  - `backend/tests/integration/test_dataset_api.py`
  - `backend/tests/integration/test_dataset_pipeline.py`

## 12. Actual Results
- 65 tests passed (143 cumulative project tests passed, 0 failures).
- Zero data leakage detected; attempts to include `observed_rainfall_mm` in feature matrices were blocked by `LeakageGuard`.
- Successfully generated `ramp_dataset_v0.3.0` with 1,200 training samples, 300 validation samples, and 300 test samples.

## 13. Real vs Synthetic Status
- **REAL TRAINING DATA: NOT AVAILABLE**.
- Dataset was synthesized via `SyntheticNWPProvider` to ensure full structural compliance while awaiting official IMD/NCMRWF archives. The metadata explicitly documents `data_mode: "SYNTHETIC_DEMO"`.

## 14. Limitations
- Gridded elevation (DEM) and coastline distance were populated using spatial corridors pending ingestion of high-resolution GeoTIFF rasters.
- Radar reflectivity and satellite infrared channels were reserved for future feature specifications.

## 15. Security / Leakage Considerations
- `LeakageGuard` audits all feature lists before model fitting.
- Test-set statistics are never utilized to scale training features (scalers fitted strictly on training data).

## 16. Reproducibility
```bash
# Execute Phase 3 verification tests
$env:PYTHONPATH=".;backend/src"
python -m pytest backend/tests/unit/dataset/ backend/tests/integration/test_dataset_api.py -v
```

## 17. Outputs
- `data/processed/training/ramp_dataset_v0.3.0/train.parquet`
- `data/processed/training/ramp_dataset_v0.3.0/val.parquet`
- `data/processed/training/ramp_dataset_v0.3.0/test.parquet`
- `data/processed/training/ramp_dataset_v0.3.0/dataset_version.json`
- Feature and target registries.

## 18. Next Phase Dependency
Phase 3 produced the canonical feature set, temporal splits, and Parquet data files consumed by Phase 4 to construct physics-informed indicators and train calibrated weather regime classifiers.
