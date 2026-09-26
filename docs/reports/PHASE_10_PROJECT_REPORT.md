# RAMP Phase 10 — Scientific Verification, Explainability & Jury Demo
## Project Report

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Phase:** 10 of 10 — Scientific Verification, Explainability & Operational Jury Demonstration  
**Version:** `scientific_v1.0.0`  
**Status:** ✅ COMPLETE

---

> **DATA MODE WARNING**
> Real IMD/NCMRWF observational archives are **NOT** currently mounted.
> All metrics are derived from synthetic test partitions, clearly labeled `SYNTHETIC_DEMO`.
> Operational accuracy cannot be claimed from these figures.
> No real observations, real SHAP values, real operational warnings, or real-world
> disaster predictions have been fabricated.

---

## 1. Phase Objectives

Phase 10 provides scientifically transparent verification of the full RAMP pipeline built
across Phases 1–9. It answers 10 scientific questions:

| # | Scientific Question | Engine |
|---|---|---|
| 1 | How does RAMP MoE RMSE compare to Raw NWP? | `ScientificVerificationEngine` |
| 2 | Does RAMP improve CSI for heavy rain (≥64.5 mm)? | `ThresholdVerificationEngine` |
| 3 | Which weather regime shows the highest RAMP improvement? | `RegimeStratifiedVerification` |
| 4 | Does RAMP performance degrade with lead time? | `LeadTimeVerification` |
| 5 | Are Phase 7 extreme probabilities well-calibrated? | `CalibrationAnalyzer` |
| 6 | Is RAMP improvement over RAW_NWP statistically significant? | `BootstrapSignificanceEngine` |
| 7 | Where does RAMP fail (underprediction, missed heavy, false alarms)? | `FailureAnalysisEngine` |
| 8 | What features drive the RAMP prediction? | `FeatureAttributionEngine` |
| 9 | Which expert dominates for each weather regime? | `ExpertGatingAnalyzer` |
| 10 | Can a complete pipeline T0→Verification be reproduced? | `CaseStudyReplayEngine` |

---

## 2. Architecture

### 2.1 ML Modules (`ml/scientific/`)

| Module | Purpose |
|--------|---------|
| `validation.py` | Scientific contracts, frozen model guard, leakage detection |
| `registry.py` | Immutable run manifests, SHA-256 cache keys, provenance |
| `verification.py` | Continuous metrics (RMSE, MAE, Bias, Pearson r, Spearman r) |
| `thresholds.py` | Contingency tables: POD, FAR, CSI, ETS, Bias Score (4 IMD thresholds) |
| `calibration.py` | Reliability diagrams, Brier Score, BSS, ECE, MCE, Log-Loss |
| `regimes.py` | Regime-stratified verification (forecast-time regimes only) |
| `lead_time.py` | Day 1–5 degradation curves |
| `spatial.py` | Phase 9 district/grid consumption and spatial error maps |
| `significance.py` | Paired bootstrap 95% CI, factual labels: LOWER_RMSE / NOT_SIGNIFICANT |
| `failure_analysis.py` | Missed heavy, false alarms, underpredictions, large divergence |
| `feature_attribution.py` | LightGBM gain/split importance, SHAP (graceful fallback) |
| `expert_analysis.py` | Regime × Expert gate matrix, gate entropy |
| `explainability.py` | Integrated single-prediction explanation engine |
| `case_study.py` | 5 synthetic case studies with 9-stage pipeline replay |
| `benchmarks.py` | Consolidated 6-model comparison tables |
| `report.py` | JSON + CSV + Markdown report generator (21 files) |
| `__main__.py` | 14-command CLI |

### 2.2 REST API (`backend/src/ramp/api/v1/scientific.py`)

19 endpoints under `/api/scientific/*`:

```
GET /api/scientific/status
GET /api/scientific/verification
GET /api/scientific/thresholds
GET /api/scientific/regimes
GET /api/scientific/lead-time
GET /api/scientific/spatial
GET /api/scientific/fss
GET /api/scientific/calibration
GET /api/scientific/bootstrap
GET /api/scientific/failures
GET /api/scientific/cases
GET /api/scientific/case/{case_id}
GET /api/scientific/explainability
GET /api/scientific/shap
GET /api/scientific/features
GET /api/scientific/experts
GET /api/scientific/provenance
GET /api/scientific/report
GET /api/scientific/jury-demo
```

Every response follows the standard Phase 10 envelope:
```json
{
  "data_mode": "SYNTHETIC_DEMO",
  "model_version": "ramp_v1.0.0",
  "scientific_version": "scientific_v1.0.0",
  "run_id": "api_...",
  "timestamp": "...",
  "availability_status": "...",
  "provenance": {...},
  "data": {...}
}
```

### 2.3 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| `Verification.tsx` | `/verification` | 7-tab scientific verification dashboard |
| `Explainability.tsx` | `/explainability` | 4-tab XAI dashboard |
| `JuryDemo.tsx` | `/jury-demo` | Interactive jury demonstration |

---

## 3. Scientific Integrity Guarantees

### 3.1 Leakage Prevention
- `ScientificValidator.check_leakage()` runs before every attribution
- 15 forbidden leakage variables listed in `LEAKAGE_FEATURES`
- If leakage detected: returns `LEAKAGE_DETECTED`, stops attribution

### 3.2 Frozen Model Protection
- `FROZEN_MODEL_REGISTRY` enforces exact model versions
- Any version mismatch returns `FROZEN_MODEL_VIOLATION` error
- Phase 10 consumes model outputs — never modifies model weights

### 3.3 Factual Metric Labels
- Labels: `LOWER_RMSE`, `NOT_SIGNIFICANT`, `SAMPLE_LIMITED`, `NOT_AVAILABLE`
- Never used: "winner", "best model", "superior", subjective rankings
- All metrics carry `n_samples` for statistical context

### 3.4 SHAP Graceful Fallback
- SHAP attempted via `TreeExplainer`
- If `shap` not installed → `SHAP_NOT_AVAILABLE`
- Fallback: LightGBM gain importance (labeled `FEATURE_IMPORTANCE_AVAILABLE`)

### 3.5 Provenance & Reproducibility
- Every run: SHA-256 cache key, UUID run ID, immutable JSON manifest
- Fixed seed: `random_seed=42`, `bootstrap_samples=300`
- All manifests persisted to `data/audit/scientific/`

---

## 4. Verification Results Summary (SYNTHETIC_DEMO)

| Model | RMSE (mm) | MAE (mm) | n |
|-------|-----------|----------|---|
| RAW_NWP | 6.37 | 4.27 | 200 |
| MEAN_BIAS | 5.06 | 3.54 | 200 |
| QUANTILE_MAPPING | 4.52 | 3.10 | 200 |
| GLOBAL_ML | 4.13 | 2.86 | 200 |
| RAMP_MOE | 3.60 | 2.49 | 200 |
| RAMP_EXTREME | 3.41 | 2.37 | 200 |

**Note:** All values from synthetic test partition. Real operational accuracy cannot be claimed.

---

## 5. CLI Reference

```bash
# Inspect engine status
python -m ml.scientific inspect

# Compute continuous metrics
python -m ml.scientific verify

# Regime-stratified
python -m ml.scientific regimes

# Lead-time curves
python -m ml.scientific lead-time

# Explainability
python -m ml.scientific explain

# Full pipeline
python -m ml.scientific pipeline

# Generate all reports
python -m ml.scientific report

# Jury demo data
python -m ml.scientific jury-demo
```

---

## 6. Generated Report Files

21 files in `data/scientific_reports/` and `data/scientific_exports/`:

| File | Content |
|------|---------|
| `verification_report.json` | Full benchmark across all metrics |
| `verification_report.md` | Markdown summary |
| `verification.csv` | Continuous metrics CSV |
| `threshold_report.json` | Threshold metrics JSON |
| `threshold_metrics.csv` | Threshold metrics CSV |
| `regime_report.json` | Regime-stratified JSON |
| `regime_metrics.csv` | Regime metrics CSV |
| `lead_time_report.json` | Lead-time curves JSON |
| `lead_time_metrics.csv` | Lead-time CSV |
| `calibration_report.json` | Calibration analysis |
| `bootstrap_report.json` | Bootstrap results |
| `bootstrap_results.csv` | Bootstrap CSV |
| `failure_analysis.json` | Failure summary |
| `failure_cases.csv` | Failure case catalog |
| `explainability_report.json` | Explanation example |
| `expert_analysis.json` | Regime × Expert matrix |
| `case_study_report.json` | Case study pipeline |
| `case_studies.json` | Case studies export |
| `spatial_verification.json` | Spatial verification |
| `feature_importance.csv` | Feature importance CSV |
| `provenance.json` | Run provenance |

---

## 7. Data Availability Matrix

| Data Type | Status | Notes |
|-----------|--------|-------|
| IMD Gridded Rainfall | NOT_AVAILABLE | Real archives not mounted |
| NCMRWF NWP Archive | NOT_AVAILABLE | Real archives not mounted |
| Radar Composite | NOT_AVAILABLE | No radar grids mounted |
| SHAP Values | SHAP_NOT_AVAILABLE | `shap` package required |
| FSS Scores | NOT_AVAILABLE | Needs observed grids |
| Historical Verification | SYNTHETIC_DEMO | From test partition |
| Feature Importance | FEATURE_IMPORTANCE_AVAILABLE | LightGBM gain |
| Case Studies | SYNTHETIC_DEMO | 5 labeled synthetic cases |

---

## 8. Phase Dependencies

```
Phase 4  → Regime probabilities consumed by ExplainabilityEngine
Phase 5  → Baseline RMSE used as benchmark reference
Phase 6  → RAMP MoE predictions evaluated
Phase 7  → Extreme probabilities evaluated by CalibrationAnalyzer
Phase 8  → Operational verification layer consumed
Phase 9  → District products consumed by SpatialVerificationEngine
```

All Phases 1–9 are **FROZEN**. Phase 10 only reads their outputs.

---

## 9. Phase 11 Readiness (Description Only)

> **DO NOT IMPLEMENT PHASE 11.**

Phase 11 (Real Data Integration) could consume Phase 10's outputs as follows:
- Mount real IMD gridded observations → enable real verification metrics
- Mount real NCMRWF NWP archive → enable real model comparison
- Install `shap` package → enable SHAP TreeExplainer attribution
- Mount radar composites → enable real FSS computation
- Deploy operationally → transition `data_mode` from `SYNTHETIC_DEMO` to `REAL_OPERATIONAL`
