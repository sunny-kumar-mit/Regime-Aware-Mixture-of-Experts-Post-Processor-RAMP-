# Meteorological Data Quality & Sanity Report

**Dataset ID:** `ramp_synthetic_monsoon_demo_v1`  
**Dataset Version:** `v1.0.0`  
**Data Mode:** `SYNTHETIC_DEMO`  
**Overall Status:** `PASS`  
**Generated At:** `2026-09-26T04:47:52.929372Z`  

---

## 1. Executive Summary
- **Total Records Ingested:** 360
- **Valid Records Passed:** 360 (100.00%)
- **Rejected Records:** 0
- **Duplicate Records Filtered:** 0
- **Physical Invalid Rainfall:** 0
- **Extreme But Valid Events Preserved (>=204.5 mm):** 2
- **Missing Target Records (Evaluation Unavailable):** 0

---

## 2. 13-Point Meteorological QC Verification

| ID | Check Name | Status | Severity | Affected Count | Diagnostic Details |
|---|---|---|---|---|---|
| 1 | Missing Mandatory Coordinates | **PASS** | INFO | 0 | 0 records have missing latitude or longitude. |
| 2 | NaN in NWP Rainfall | **PASS** | INFO | 0 | 0 records have NaN in nwp_rainfall_mm. |
| 3 | Infinity Detection | **PASS** | INFO | 0 | 0 records contain infinite values across numeric columns. |
| 4 | Rainfall Sanity & Extreme Preservation | **PASS** | INFO | 0 | 0 records failed physical limits (<0 or >1500.0 mm). Distinguished 2 EXTREME_BUT_VALID records (>=204.5 mm) preserved. |
| 5 | Duplicate Timestamp & Spatial Point Detection | **PASS** | INFO | 0 | 0 duplicate records identified on (forecast_valid_time, latitude, longitude, lead_time_hours). |
| 7 | Global Coordinate Range Check | **PASS** | INFO | 0 | 0 records outside [-90,90] lat or [-180,180] lon. |
| 8 | Indian Regional Domain Diagnostic | **PASS** | INFO | 0 | 0 records lie outside primary Indian subcontinent box. Preserved. |
| 9 | Rainfall Unit Consistency Check | **PASS** | INFO | 0 | Rainfall magnitude consistent with mm. |
| 10 | Timezone Consistency Audit | **PASS** | INFO | 0 | Timestamps successfully verified as UTC / consistent. |
| 11 | Forecast Temporal Progression Alignment | **PASS** | INFO | 0 | 0 records had valid_time before initialization_time. |
| 12 | Lead-Time Integrity | **PASS** | INFO | 0 | 0 records missing lead_time_hours. |
| 13 | Ground-Truth Observation Availability | **PASS** | INFO | 0 | 0 records lack ground truth observed_rainfall_mm. Marked EVALUATION_UNAVAILABLE (NOT assumed zero). |

---

## 3. Spatio-Temporal and Variable Coverage
- **Temporal Range:** 2025-07-02 00:00:00+00:00 to 2025-07-22 00:00:00+00:00
- **Spatial Domain:** Lat [21.00, 21.50], Lon [78.00, 78.50]
- **Lead Times Available:** [24, 48]

## 4. Rejection Audit Breakdown
- *Zero records rejected.*