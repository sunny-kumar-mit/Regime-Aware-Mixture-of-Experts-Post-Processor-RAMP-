# RAMP Dataset Versioning & Provenance Architecture

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.versioning.DatasetVersionManager`

---

## 1. Versioning Semantics

Dataset versions follow the format:
`ramp_dataset_v<major>.<minor>.<patch>`

A dataset version changes whenever:
- A new source provider or time range is ingested (minor/patch).
- The feature registry schema is updated (minor).
- Target thresholds or definitions are altered (major).
- Splitting or purge gap parameters change (minor).
- Preprocessing or imputation strategies change (minor).

---

## 2. Manifest Specifications

### `dataset_version.json`
Stores metadata and provenance:
```json
{
  "dataset_id": "ramp_dataset_v0.3.0",
  "version": "0.3.0",
  "created_at": "2026-09-25T21:06:55.094104",
  "data_mode": "SYNTHETIC_DEMO",
  "source_datasets": ["SYNTHETIC_GFS", "SYNTHETIC_IMD"],
  "feature_schema_version": "1.0.0",
  "target_schema_version": "1.0.0",
  "split_version": "1.0.0",
  "preprocessing_version": "1.0.0",
  "row_count": 360,
  "feature_count": 27,
  "target_count": 6,
  "time_range": {
    "start": "2025-07-02T00:00:00+00:00",
    "end": "2025-07-22T00:00:00+00:00"
  },
  "spatial_range": {
    "lat_min": 21.0,
    "lat_max": 21.5,
    "lon_min": 78.0,
    "lon_max": 78.5
  },
  "checksum": "sha256_hash_here"
}
```

### `split_manifest.json`
Specifies temporal boundaries and sample counts per partition:
```json
{
  "split_type": "chronological",
  "train_range": {
    "start": "2025-07-02T00:00:00+00:00",
    "end": "2025-07-15T00:00:00+00:00"
  },
  "val_range": {
    "start": "2025-07-16T00:00:00+00:00",
    "end": "2025-07-18T00:00:00+00:00"
  },
  "test_range": {
    "start": "2025-07-19T00:00:00+00:00",
    "end": "2025-07-22T00:00:00+00:00"
  },
  "train_rows": 243,
  "val_rows": 54,
  "test_rows": 63,
  "purge_gap_hours": 24
}
```

### `DATASET_CARD.md`
Human-readable Markdown document summarizing the dataset purpose, dimensions, class imbalance, and leakage guard audit.
