# PHASE 2 PROJECT REPORT — Meteorological Data Layer

**Project:** RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Status:** COMPLETE  

---

## 1. Executive Summary
Phase 2 built the end-to-end meteorological data layer for RAMP. It implemented provider abstractions for atmospheric model data and observational archives, handling heterogeneous NetCDF/GRIB formats, spatial regridding to the canonical 0.25° India grid (6.5°N–38.5°N, 66.5°E–100.5°E), unit conversions, time harmonization (UTC to IST and cumulative accumulations), and data quality validation. Crucially, Phase 2 implemented strict meteorological honesty: NCMRWF and GFS adapters honestly report `UNAVAILABLE` when live real archives are absent, and fallback to `SYNTHETIC_DEMO` providers without fabricating artificial atmospheric measurements.

## 2. Problem Addressed
Meteorological post-processing pipelines suffer from severe integration friction: differing coordinate frames (e.g. GFS 0.25° vs NCUM 0.12°), varying vertical coordinates, inconsistent precipitation units (kg m⁻² s⁻¹ vs mm/6h vs accumulated mm), and missing quality flags. Phase 2 eliminated these incompatibilities by enforcing canonical standards at the ingestion boundary.

## 3. Objective
- Abstract NWP and observation providers under a unified interface (`BaseMeteorologicalProvider`).
- Implement adapters for GFS, GEFS, NCMRWF (NCUM/NEPS), and IMD 0.25° gridded observations.
- Harmonize units to canonical standards (rainfall in mm, winds in m/s, pressure in Pa, temperature in K).
- Standardize spatial dimensions onto the India 0.25° grid (129 latitude × 137 longitude cells = 17,673 points).
- Establish data provenance tracking with SHA-256 checksums and quality flag audits.

## 4. Architecture
```
  [GFS / GEFS]    [NCMRWF NCUM/NEPS]    [IMD Gridded Obs]    [Synthetic Generator]
        │                  │                    │                     │
        └──────────────────┼────────────────────┴─────────────────────┘
                           ▼
             BaseMeteorologicalProvider Interface
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
  Unit Conversion     Time Harmonization   Bilinear Spatial Regrid
  (kg/m²s -> mm)       (UTC/Accumulation)   (-> 0.25° India Grid)
       └───────────────────┼───────────────────┘
                           ▼
                  Quality Validation &
                SHA-256 Provenance Audit
                           │
                           ▼
             Canonical NetCDF4 / Zarr Store
```

## 5. Implementation
- **Provider Framework (`ramp.data.providers`):** `BaseNWPProvider`, `BaseObservationProvider`, and concrete implementations for GFS, NCMRWF, IMD, and Synthetic demo datasets.
- **Harmonization Engine (`ramp.data.harmonisation`):** Unit normalizer converting Kelvin/Celsius, Pa/hPa, kg m⁻² s⁻¹ to mm, and knots to m/s; temporal harmonizer aligning forecast cycles with 24-hour IMD verification windows (03:00 UTC / 08:30 IST); bilinear spatial regridder.
- **Quality Engine (`ramp.data.validation`):** Flagging system auditing missingness, NaN, inf, negative rainfall (strictly invalid), and physical bounds violations.

## 6. Data Flow
1. Raw forecast cycles or observation files are presented to the respective provider adapter.
2. Provider checks local staging paths; if files are absent, raises `ProviderUnavailableError` (never fabricates).
3. When present or in `SYNTHETIC_DEMO` mode, raw grids are ingested as xarray datasets.
4. Harmonizer converts variables to canonical units and regrids spatially to `GridSpec(0.25°, 6.5..38.5°N, 66.5..100.5°E)`.
5. Quality validator checks bounds, generates `ValidationReport`, appends SHA-256 provenance steps, and writes standardized arrays.

## 7. Algorithms / Methodology
- **Spatial Regridding:** Scipy/xarray regular-grid bilinear interpolation onto the 0.25° India bounding box.
- **Precipitation Conversion:**
  $$\text{Rainfall (mm)} = \text{flux} \, (\text{kg}\,\text{m}^{-2}\,\text{s}^{-1}) \times \Delta t \, (\text{seconds})$$
- **Quality Auditing:** Bitwise quality flags (`VALID`, `MISSING`, `INVALID`, `ESTIMATED`, `EXTREME`).

## 8. Files & Modules
- `backend/src/ramp/data/providers/base.py`: Provider abstract base classes, `GridSpec`, `BoundingBox`.
- `backend/src/ramp/data/providers/gfs.py`: GFS 0.25° NWP provider.
- `backend/src/ramp/data/providers/ncmrwf.py`: NCMRWF NCUM/NEPS provider with honest unavailable behavior.
- `backend/src/ramp/data/providers/synthetic.py`: Physics-consistent synthetic generator for pipeline testing.
- `backend/src/ramp/data/harmonisation/units.py`: Unit conversions and canonical aliases.
- `backend/src/ramp/data/harmonisation/regrid.py`: Bilinear spatial interpolator.
- `backend/src/ramp/data/validation/quality.py`: Quality flag auditing and summary statistics.
- `backend/src/ramp/api/v1/data.py`: Data ingestion status and catalogue REST endpoints.

## 9. APIs
- `GET /api/data/status`: Availability of all registered providers.
- `GET /api/data/providers`: Detailed provider capabilities, grid specifications, and real-data flags.
- `GET /api/data/catalogue`: Listing of ingested raw files, sizes, and provenance records.

## 10. Frontend
- `/data` (`DataFeeds.tsx`) route displaying provider status cards (GFS, GEFS, NCMRWF, IMD).
- Visual warning badges distinguishing `SYNTHETIC DEMO` from `REAL` data feeds.
- Ingestion telemetry table with grid coordinates and variable metadata.

## 11. Testing
- 74 comprehensive unit tests in:
  - `backend/tests/unit/harmonisation/test_units.py`
  - `backend/tests/unit/ingestion/test_providers.py`
  - `backend/tests/unit/validation/test_quality.py`
  - `backend/tests/integration/test_data_api.py`

## 12. Actual Results
- 74 tests executed and passed (0 failures).
- Unit conversion accuracy verified within float precision tolerances.
- Negative precipitation correctly rejected as invalid.

## 13. Real vs Synthetic Status
- **REAL DATA: NOT AVAILABLE**.
- NCMRWF and IMD adapters accurately reported `is_available = False` because authoritative archives were not present in local storage. Pipeline executed reliably using `SyntheticNWPProvider`.

## 14. Limitations
- High-resolution orographic sub-grid DEM parsing was not yet integrated into tabular features.
- Dynamic cyclone track extraction from text bulletins was not implemented.

## 15. Security / Leakage Considerations
- Path traversal prevention in provider file loading.
- Cryptographic SHA-256 hashing on all ingested NetCDF/GRIB assets.

## 16. Reproducibility
```bash
# Execute Phase 2 verification tests
$env:PYTHONPATH=".;backend/src"
python -m pytest backend/tests/unit/harmonisation/ backend/tests/unit/ingestion/ backend/tests/unit/validation/ -v
```

## 17. Outputs
- Fully functioning ingestion, regridding, unit conversion, and validation engines.
- Ingestion REST endpoints.
- `/data` dashboard view.

## 18. Next Phase Dependency
Phase 2 provided the normalized, regridded 0.25° spatio-temporal datasets and variables required for Phase 3 to extract tabular predictor features and canonical observation targets.
