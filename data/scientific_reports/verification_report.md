# RAMP Phase 10 — Scientific Verification Report

**Run ID:** `sci_20260926_060010_2c0fc50d`
**Generated:** 2026-09-26 06:00:10 UTC
**Data Mode:** `SYNTHETIC_DEMO`
**Scientific Version:** `scientific_v1.0.0`

> **⚠️ REAL IMD/NCMRWF OBSERVATIONAL ARCHIVES ARE NOT CURRENTLY MOUNTED.**
> All metrics are derived from synthetic test partitions and must be labeled
> **SYNTHETIC DEMONSTRATION ONLY**. Real-world operational accuracy cannot be claimed.

---

## 1. Continuous Metrics Summary

| Model | RMSE (mm) | MAE (mm) | Bias (mm) | Pearson r | Samples |
|-------|-----------|----------|-----------|-----------|---------|
| RAW_NWP | 6.3675 | 4.8874 | 3.0299 | 0.7716 | 200 |
| MEAN_BIAS | 5.0641 | 3.8681 | 0.8806 | 0.8201 | 200 |
| QUANTILE_MAPPING | 4.5227 | 3.4395 | 0.679 | 0.8387 | 200 |
| GLOBAL_ML | 4.0706 | 3.1038 | 1.0689 | 0.8766 | 200 |
| RAMP_MOE | 3.6069 | 2.8091 | 0.9418 | 0.9012 | 200 |
| RAMP_EXTREME | 3.6268 | 2.7379 | 0.5206 | 0.8886 | 200 |

*Factual labels only: LOWER_RMSE, NOT_SIGNIFICANT, SAMPLE_LIMITED. No model is ranked 'best'.*

---

## 2. Regime-Stratified Verification

| Regime | RMSE | MAE | Heavy CSI | Samples |
|--------|------|-----|-----------|---------|
| ACTIVE_MONSOON | 2.4994 | 2.0223 | None | 42 |
| BREAK_MONSOON | 1.4959 | 1.1715 | None | 25 |
| LOW_DEPRESSION | 4.4623 | 3.2454 | None | 18 |
| COASTAL | 3.0908 | 2.3161 | None | 30 |
| OROGRAPHIC | 5.7101 | 4.2736 | None | 20 |
| WESTERN_DISTURBANCE | 2.7679 | 2.0842 | None | 28 |
| TRANSITION_OTHER | 1.7283 | 1.3373 | None | 37 |

---

## 3. Data Mode & Real Data Policy

| Field | Value |
|-------|-------|
| Data Mode | `SYNTHETIC_DEMO` |
| Real Observations | NOT AVAILABLE |
| SHAP Attribution | SHAP_NOT_AVAILABLE (graceful fallback to gain importance) |
| FSS Observations | NOT_AVAILABLE (no real radar/gauge grids mounted) |
| Operational Accuracy | Cannot be claimed |

---

## 4. Generated Artifacts

- `bootstrap_report.json`
- `bootstrap_results.csv`
- `calibration_report.json`
- `case_studies.json`
- `case_study_report.json`
- `expert_analysis.json`
- `explainability_report.json`
- `failure_analysis.json`
- `failure_cases.csv`
- `feature_importance.csv`
- `lead_time_metrics.csv`
- `lead_time_report.json`
- `provenance.json`
- `regime_metrics.csv`
- `regime_report.json`
- `spatial_verification.json`
- `threshold_metrics.csv`
- `threshold_report.json`
- `verification.csv`
- `verification_report.json`