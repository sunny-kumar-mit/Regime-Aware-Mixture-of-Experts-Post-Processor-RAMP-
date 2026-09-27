# RAMP Phase 11 — Real Data Activation & Operational Data Plane
## Project Report

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Phase:** 11 — Real Data Activation & Operational Data Plane  
**Status:** COMPLETE  
**Date:** 2026-09-26  
**Lead AI / Weather-Science Architect:** Antigravity (Google DeepMind)

---

## 1. Executive Summary

Phase 11 transitions the RAMP post-processing platform from a `SYNTHETIC_DEMO`-first operating stance into a **fully functional, real-data-capable operational data plane**. 

All scientific foundations developed during Phases 1–10 remain completely intact without regression. Phase 11 establishes strict architectural contracts for real meteorological data ingestion, metadata extraction, chain-of-custody provenance, provider hierarchy prioritization, dynamic forecast cycle discovery, CF metadata inspection, native grid vs RAMP grid harmonisation, and temporal observation matching with anti-leakage guards.

---

## 2. Key Deliverables & Technical Architecture

### 2.1 Real Data Source Priority Hierarchy (`backend/src/ramp/data_plane/sources.py`)

An explicit provider tier hierarchy is enforced across all data ingestion and discovery workflows:

- **PRIMARY (Operational MoES/NCMRWF Stream):**
  - `ncmrwf_ncum`: NCMRWF NCUM Unified Model Deterministic (~0.12° / 12km native resolution)
  - `ncmrwf_neps`: NCMRWF NEPS Ensemble Prediction System (~0.12° native resolution, 23 members)
  - `imd_obs`: IMD 0.25° Gridded Daily Rainfall Observations (ground truth)
- **SECONDARY (Public Proxy / Backup):**
  - `gfs`: NCEP Global Forecast System (0.25° native resolution)
  - `gefs`: NCEP Global Ensemble Forecast System (0.50° native resolution)
- **DEMO (Simulation):**
  - `synthetic_demo`: Artificial meteorological demonstration generator

**Critical Integrity Contract:**
- Sources are **never silently substituted**.
- `PUBLIC_PROXY` sources (e.g. GFS, GEFS) are **never labeled as NCMRWF or REAL_OPERATIONAL**.
- Every dataset exposes:
  `source_provider`, `source_model`, `initialization_time`, `forecast_valid_time`, `cycle`, `lead_time_hours`, `native_resolution`, `target_resolution`, `variables`, `units`, `data_mode`, `file_name`, `file_hash`, `ingestion_timestamp`, `quality_status`, `provenance`.

### 2.2 Operational Data Modes

Five distinct operational modes are enforced:
1. `REAL_OPERATIONAL`: Real NCMRWF/IMD operational data stream.
2. `REAL_ARCHIVE`: Historical real observational and reanalysis archives.
3. `PUBLIC_PROXY`: Real public NWP or observation sources (e.g., GFS/GEFS) — strictly distinct from NCMRWF.
4. `SYNTHETIC_DEMO`: Artificial physics-informed demonstration data.
5. `NOT_AVAILABLE`: No valid data source found in local storage.

### 2.3 Actual Data Discovery Service (`backend/src/ramp/data_plane/discovery.py`)

`DataDiscoveryService` scans active storage directories dynamically:
- `data/raw/nwp/ncmrwf/ncum/`
- `data/raw/nwp/ncmrwf/neps/`
- `data/raw/nwp/gfs/`
- `data/raw/nwp/gefs/`
- `data/raw/observations/imd/`

It inspects file headers, computes SHA-256 checksums, discovers forecast cycles and lead times, catalogs variables, and evaluates overall operational availability.

### 2.4 CF Metadata Inspector & NetCDF/GRIB Ingestion Engine (`backend/src/ramp/data_plane/cf_reader.py`)

- **CF Conventions:** Complies with CF-1.6 / CF-1.8 metadata standards.
- **Coordinate Discovery:** Discovers `lat`, `lon`, `time`, and vertical pressure `level` (`plev`, `isobaricInhPa`).
- **Coordinate Normalization:** Automatically detects latitude ordering (ascending vs. descending) and normalizes longitude domains (-180..180 vs. 0..360) to the India bounding box ($6.5^\circ\text{N} - 38.5^\circ\text{N}$, $66.5^\circ\text{E} - 100.5^\circ\text{E}$).
- **Unit Verification:** Reads units directly from file attributes (e.g. `kg/m^2`, `Pa`, `K`, `m/s`); never assumes units without metadata inspection.
- **Quality & Corruption Quarantine:** Detects NaNs, `_FillValue`, -999.0, duplicate timestamps, and quarantines corrupted binary files without service crash.

### 2.5 Forecast Cycle Model & Arbitrary Lead Discovery (`backend/src/ramp/data_plane/cycle.py`)

- **First-Class ForecastCycle Object:**
  Exposes `cycle_id`, `date`, `cycle_utc` (`00 UTC`, `06 UTC`, `12 UTC`, `18 UTC`), `model`, `initialization_time`, `available_leads`, `status`, and `files`.
- **Dynamic Lead Discovery:**
  Does **not** hardcode $[24, 48, 72, 96, 120]$. Derives arbitrary available lead steps from actual files ($6\text{h}, 12\text{h}, 18\text{h}, 24\text{h} \dots 120\text{h}+$).
- **No Cycle Fabrication:** Only cycles with actual file artifacts on disk are exposed.

### 2.6 NCMRWF Native Grid vs RAMP Grid Harmonisation (`backend/src/ramp/data_plane/regridding.py`)

Preserves native resolution while ensuring uniform input dimensions to the RAMP MoE gating network:
$$\text{NCMRWF Native Grid (0.12° / 12km)} \longrightarrow \text{Quality Control} \longrightarrow \text{RAMP Harmonisation} \longrightarrow \text{0.25° Canonical RAMP Grid}$$
- Employs mass-conserving interpolation for rainfall.
- Metadata explicitly stores both `native_resolution: 0.12` and `ramp_resolution: 0.25`.
- Clearly documents: *"RAMP grid (0.25°) is a harmonised operational canonical grid for multi-model post-processing. It is NOT the native NCMRWF model resolution."*

### 2.7 IMD Observation Ingestion & NWP Matching Engine (`backend/src/ramp/data_plane/matcher.py`)

- **Matching Key:** `forecast_valid_time == observation_time` ($\text{valid\_time} = \text{init\_time} + \text{lead\_hours}$).
- **Temporal Anti-Leakage Guard:** Verification that observation timestamp does not post-date prediction execution.
- **Match Status Categories:** `MATCHED`, `PARTIAL`, `MISSING_OBSERVATION`, `MISSING_FORECAST`, `MISALIGNED`.
- **Zero-Fill Prohibition:** Missing observations are **never converted into 0 mm**. Preserving genuine nulls prevents artificial low-bias calibration in the gating network.
- **Extreme Rainfall Preservation:** Extreme-but-valid observed events ($> 204.5\text{ mm}$) are flagged `VALID_EXTREME` and preserved.

---

## 3. Operational REST API (`backend/src/ramp/api/v1/data.py`)

All endpoints return a uniform contract:
```json
{
  "data_mode": "SYNTHETIC_DEMO | REAL_OPERATIONAL | PUBLIC_PROXY",
  "source": "DataDiscoveryService | CycleManager | DataMatchingEngine",
  "timestamp": "2026-09-26T18:30:00Z",
  "provenance": { ... },
  "availability_status": "AVAILABLE | NOT_AVAILABLE | OPERATIONAL | MATCHED",
  "data": { ... }
}
```

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/data/sources` | Explicit provider hierarchy, tiers, and operational scan results |
| `GET` | `/api/data/cycles` | Discovered forecast cycles (00, 06, 12, 18 UTC) and lead steps |
| `GET` | `/api/data/cycles/{id}` | Detailed file manifest and checksums for a specific cycle |
| `GET` | `/api/data/availability` | Live 4-point operational matrix (NCUM, NEPS, IMD, RAMP) |
| `GET` | `/api/data/forecast` | NWP forecast metadata, native vs RAMP resolution, variable inventory |
| `GET` | `/api/data/observations` | IMD observation inspection, QC flags, rainfall statistics |
| `GET` | `/api/data/match` | NWP + IMD matching engine run, anti-leakage verification |
| `GET` | `/api/data/provenance` | Complete chain-of-custody provenance records and SHA-256 hashes |
| `GET` | `/api/data/quality` | Data quality audit, corrupted file counts, CF compliance status |

---

## 4. Frontend Operational UI & Live Status Header

### 4.1 Live Header Status Indicators (`frontend/src/components/layout/Shell.tsx`)
The top navbar permanently displays live operational status badges:
- **NCMRWF NCUM:** `● AVAILABLE` / `● NOT AVAILABLE`
- **NEPS:** `● AVAILABLE` / `● NOT AVAILABLE`
- **IMD OBS:** `● AVAILABLE` / `● NOT AVAILABLE`
- **RAMP MODEL:** `● READY` / `● NOT READY`
- **Integrity Mode:** `Mode: SYNTHETIC_DEMO | REAL_OPERATIONAL`

### 4.2 Operational Data Plane Page (`frontend/src/pages/DataFeeds.tsx`)
- **Scientific Honesty Notice Banner:** Prominently alerts users when raw archives are not mounted and synthetic fallback is active.
- **Provider Hierarchy Cards:** Interactive source cards for NCUM, NEPS, IMD, GFS, GEFS, and Demo with tier badges and native resolutions.
- **Operational Controls:** Dynamic dropdowns for Forecast Date, Cycle (`00`, `06`, `12`, `18 UTC`), Lead Time (`6h` to `120h+`), Variable (`precip_nwp_raw`, `u850`, `v850`, `mslp`, `t850`, `cape`), Level (`Surface`, `850`, `700`, `500`, `200 hPa`), and Region.
- **Native vs. RAMP Grid Harmonisation Card:** Visual breakdown of 0.12° native vs 0.25° canonical resolution.
- **NWP + IMD Matcher Inspector:** Real-time alignment status, offset in seconds, valid cell counts, and anti-leakage verification.
- **Discovered Forecast Cycles Table:** Discovered runs, leads, file counts, and statuses.
- **Quality & Provenance Audit Summary:** Audited files, quarantined files, and SHA-256 tracking.
- **Tab Navigation:** Instant switching between *Operational Data Plane* and *Dataset Catalog & Features*.

---

## 5. Test Suite Verification (`tests/test_phase11_data_plane.py`)

The full repository test suite was executed:
- **Phase 11 Test Suite:** 13 passed / 13 tests (100% pass rate)
  1. `test_source_discovery`: Provider hierarchy, tier ranking, and native resolutions
  2. `test_real_synthetic_classification`: Anti-mislabeling guard for secondary sources
  3. `test_cycle_discovery`: Discovery without cycle fabrication
  4. `test_lead_discovery`: Dynamic extraction of arbitrary leads (6h, 18h, 48h, 168h)
  5. `test_coordinate_detection`: CF coordinates, ordering, and resolution inspection
  6. `test_unit_detection`: Extraction of metadata-driven units (K, Pa, kg/m²)
  7. `test_timestamp_matching_and_anti_leakage`: Alignment and anti-leakage verification
  8. `test_missing_observation_handling`: Prohibition of zero-filling for missing observations
  9. `test_duplicate_timestamp_detection`: Duplicate timestamp detection in NetCDF
  10. `test_corrupted_file_handling`: Quarantine of corrupted binary files without crash
  11. `test_checksum_computation`: SHA-256 file content verification
  12. `test_native_to_ramp_regridding`: Mass-conserving 0.12° to 0.25° regridding
  13. `test_api_operational_endpoints`: Full HTTP contract checks across all 8 endpoints
- **Full Repository Suite:** **328 passed / 328 tests** across all phases with zero regressions.
- **Frontend Build:** TypeScript compilation clean (`npx tsc --noEmit` exited with code 0).
- **Interactive UI Verification:** Completed by browser subagent, recorded to `phase11_data_plane_verified_1790428626074.webp`.

---

## 6. Next Phase Handoff (Phase 12 Preview)

Phase 11 activates the operational data plane without retraining existing ML models.
In accordance with instructions:
- **ML models were NOT retrained during Phase 11.**
- **Phase 12** will utilize this operational data plane to generate the authoritative, real paired training dataset for training the production RAMP weights.
