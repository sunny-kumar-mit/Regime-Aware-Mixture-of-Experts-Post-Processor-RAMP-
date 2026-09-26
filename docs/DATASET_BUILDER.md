# RAMP Training Dataset Builder

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.builder.DatasetBuilder`

---

## 1. Overview & Architectural Role

The **Training Dataset Builder** serves as the primary bridge between Phase 2 (Raw Meteorological Ingestion & Grid Harmonisation) and Phases 4–7 (Regime Classification, Baselines, RAMP Mixture-of-Experts, and Extreme Rainfall Calibration).

```
Phase 2 Harmonised Grids (GFS, GEFS, NCMRWF, IMD 0.25°)
                           │
                           ▼
              ┌─────────────────────────┐
              │ ForecastObservationJoin │ ── (lat, lon, forecast_valid_time)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   FeatureEngineering    │ ── (wind speed/dir, cyclic doy/hour, 3x3 stats)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │     TargetBuilder       │ ── (6 targets, IMD thresholds)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  ChronologicalSplitter  │ ── (train, val, test + 24h purge gap)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Train-Only Preprocessor │ ── (fit on TRAIN only: impute, scale)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │      LeakageGuard       │ ── (10-point audit, fails loudly)
              └─────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ DatasetVersionManager   │ ── (Parquet exports, Manifests, DATASET_CARD)
              └─────────────────────────┘
```

---

## 2. Core Execution Invariants

1. **Spatio-Temporal Inner Join:**
   - Matching key: `(round(latitude, 2), round(longitude, 2), forecast_valid_time)`.
   - Never join using model initialization time alone.
   - Preserves `forecast_initialization_time`, `lead_time_hours`, and `forecast_valid_time` on every sample row.

2. **Quality Policy Enforcement:**
   - Default policy: `BALANCED`.
   - Rejects `INVALID` (e.g. negative rainfall) and `MISSING` targets.
   - Preserves `VALID_EXTREME` (e.g. rainfall > 204.5 mm up to 400+ mm) without statistical clipping.
   - Flags `SUSPICIOUS` observations for review.

3. **Zero Data Leakage:**
   - Climatology and preprocessing statistics are fitted strictly on `TRAIN`.
   - Predictor columns $X$ are audited to verify that no target observations or forecast errors enter feature space.

---

## 3. CLI Command Reference

```bash
# Build complete training dataset (using synthetic demo data when real archives are unstaged)
python -m ml.dataset build --output-dir data/processed/training/ramp_dataset_v0.3.0 --days 20 --version 0.3.0

# Validate all required manifests and checksums
python -m ml.dataset validate --dataset-dir data/processed/training/ramp_dataset_v0.3.0

# Inspect split distribution statistics and class imbalance
python -m ml.dataset stats --dataset-dir data/processed/training/ramp_dataset_v0.3.0

# View chronological split boundaries and purge gaps
python -m ml.dataset split --dataset-dir data/processed/training/ramp_dataset_v0.3.0

# Audit leakage invariants
python -m ml.dataset leakage-check --dataset-dir data/processed/training/ramp_dataset_v0.3.0

# Full comprehensive inspection
python -m ml.dataset inspect --dataset-dir data/processed/training/ramp_dataset_v0.3.0
```

---

## 4. Generated Artifacts

Every dataset build produces:
- `train.parquet`, `val.parquet`, `test.parquet`: Tabular partitions for model consumption.
- `ramp_dataset.parquet`: Combined versioned dataset.
- `inspection_sample.csv`: First 100 records for human inspection.
- `dataset_version.json`: Semantic version, row counts, and checksum.
- `split_manifest.json`: Chronological boundaries and row counts per partition.
- `preprocessing_manifest.json`: Train-fitted medians, means, and standard deviations.
- `leakage_report.json`: Audit log of all 10 leakage invariants.
- `dataset_statistics.json`: Quantiles, event counts, and class imbalance metrics.
- `feature_registry.json`: Catalog of all features, derivations, and availability.
- `target_schema.json`: Target variable definitions.
- `DATASET_CARD.md`: Human-readable scientific summary card.
