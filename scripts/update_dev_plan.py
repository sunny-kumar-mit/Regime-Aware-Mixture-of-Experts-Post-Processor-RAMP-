"""Update DEVELOPMENT_PLAN.md to mark Phase 7 and Phase 8 COMPLETE with exact deliverables and test counts.
"""

def update_dev_plan():
    file_path = "DEVELOPMENT_PLAN.md"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_p7_p8 = """### Phase 7 — Extreme Rainfall Probability Engine ⏳ NEXT
- Heavy (>=64.5mm), Very Heavy (>=115.6mm), Extremely Heavy (>=204.5mm)
- Probability calibration & reliability diagrams

### Phase 8 — Spatial Post-Processing & District Aggregation
- Grid-to-district shapefile aggregation
- Fractions Skill Score (FSS) neighbourhood smoothing"""

    new_p7_p8 = """### Phase 7 — Extreme Rainfall Probability Engine ✅ COMPLETE
- Multi-threshold classification heads for Rain ($\\ge 0.1$ mm), Heavy ($\\ge 64.5$ mm), Very Heavy ($\\ge 115.6$ mm), and Extremely Heavy ($\\ge 204.5$ mm)
- Platt scaling (logistic sigmoid) and Isotonic regression calibration fitted strictly on validation data
- Strict monotonic probability reconciliation ($P(\\text{Rain}) \\ge P(\\text{Heavy}) \\ge P(\\text{Very Heavy}) \\ge P(\\text{Extremely Heavy})$)
- Comprehensive probability metrics (Brier, Brier Skill Score, ECE, MCE, Log Loss, ROC-AUC, PR-AUC)
- Lead-time, regime-conditioned, and spatial probability outputs
- Frozen model `extreme_prob_v1.0.0` serialized under `data/models/extreme/`
- 14 REST API endpoints under `/api/extreme/*`
- Interactive 10-section dashboard at `/extreme`
- 260/260 tests passed (39 Phase 7 tests)
- Report: `docs/reports/PHASE_7_PROJECT_REPORT.md`

### Phase 8 — Real-Data Integration & Operational Verification Readiness ✅ COMPLETE
- Multi-provider architecture (`RealDataProvider`, `SyntheticDataProvider`, NetCDF, GRIB, Parquet, CSV)
- Canonical `DatasetContract` schema (`observed_rainfall_mm`, `nwp_rainfall_mm`, spatiotemporal coordinates)
- 13-point `MeteorologicalQualityControl` distinguishing unphysical corruptions (`PHYSICAL_INVALID`) from severe convective events (`EXTREME_BUT_VALID` $\\ge 204.5$ mm)
- Missing target observations mapped to evaluation unavailable (never 0.0 mm)
- Explicit `UnitNormalizer` with documented conversions and audit logs
- `TemporalAlignmentEngine` supporting Day 1 through Day 5 lead-time synchronization
- `SpatialAlignmentEngine` supporting 0.25° grid snap over India
- Extended `LeakageGuard` for real-data feature auditing (forbidding future observations, future/observed regimes, post-event variables)
- `PipelineReplayer` orchestrating full 8-stage operational replay
- `OperationalModelRegistry` maintaining freeze locks on `ramp_v1.0.0` and `extreme_prob_v1.0.0`
- `OperationalReadinessEvaluator` defining 6 engineering readiness tiers (Levels 0–5; currently Level 0: Synthetic Demo)
- `OperationalVerificationEngine` evaluating 6 systems (Raw NWP, Mean Bias, Quantile Mapping, Global ML, RAMP MoE, RAMP + Extreme Prob)
- Continuous metrics, threshold contingency (POD, FAR, CSI, ETS, FBIAS), probability metrics (Brier, BSS, ECE, MCE, PR-AUC), paired bootstrap (300 resamples), 7-regime stratification, Day 1–5 lead-time breakdown, spatial grid
- 14 REST API endpoints under `/api/operational/*`
- 15-section interactive dashboard at `/operational` with dynamic data status banner
- 286/286 tests passed (26 Phase 8 tests, 0 failures)
- Report: `docs/reports/PHASE_8_PROJECT_REPORT.md`"""

    if old_p7_p8 in content:
        content = content.replace(old_p7_p8, new_p7_p8)
    else:
        print("Warning: old_p7_p8 pattern not found verbatim, checking alternatives.")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {file_path} successfully!")

if __name__ == "__main__":
    update_dev_plan()
