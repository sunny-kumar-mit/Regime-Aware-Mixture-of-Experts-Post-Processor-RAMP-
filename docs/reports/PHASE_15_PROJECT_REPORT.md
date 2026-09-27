# Phase 15 Project Report: Operations Control Center

**Project**: SIH26080 - Regime-Aware Mixture-of-Experts Post-Processor (RAMP)
**Organization**: Ministry of Earth Sciences (MoES) / NCMRWF
**Status**: COMPLETE & VERIFIED (Synthetic Demonstration Mode; Real Operational Activation Ready)
**Execution Timestamp**: 2026-09-27T01:08:00Z
**Engine Version**: `v2.0.0` | **Feature Contract**: `ramp_features_v1.0.0` | **Target Contract**: `ramp_targets_v1.0.0`

---

## 1. Executive Summary

Phase 15 introduces the **Operations Control Center** -- the automated lifecycle management and operational governance layer for the RAMP system. Building on the Phase 14 forecast inference engine, Phase 15 provides orchestration infrastructure that manages the full forecast cycle lifecycle, detects system health degradation, and gatekeeps the transition from `SYNTHETIC_DEMO` to `REAL_OPERATIONAL` mode.

The implementation delivers five interlocking subsystems:

1. **11-State Lifecycle Automaton** (`ml/operations/state.py`) -- thread-safe state machine governing every forecast cycle from `INITIALIZING` through `CYCLE_COMPLETE`, with a full audit history of every transition and operator override.
2. **Idempotent Forecast Scheduler** (`ml/operations/scheduler.py`) -- background polling scheduler with SHA-256 job-ID deduplication, ensuring no forecast cycle is ever double-executed.
3. **8-Rule Alert Monitor** (`ml/operations/alerts.py`) -- real-time metric threshold evaluator with de-duplicated alert lifecycle (raise -> acknowledge -> resolve) covering failure rates, ECE calibration drift, unauthorized mode activation, and data integrity.
4. **Diagnostic Drift Monitor** (`ml/operations/drift.py`) -- covers feature drift (KS-statistic), prediction distribution drift, regime frequency drift, and calibration ECE drift across all 4 IMD rainfall thresholds. Diagnostic only -- no retraining is triggered.
5. **30-Point Production Readiness Engine** (`ml/operations/production.py`) -- evaluates 6 categories (CAT-A through CAT-F) and renders a GO / CONDITIONAL_GO / NO_GO launch verdict with per-check evidence and an immutable data honesty disclaimer.

The REST API layer adds **15 new endpoints** under `/api/operations/`, and the frontend delivers a **5-tab Operations Control Center UI** at `/operations`.

All **44 automated tests pass** in **9.10 s** on Python 3.14.2.

---

## 2. Objectives

| # | Objective | Delivered |
|---|-----------|-----------|
| 1 | 11-state lifecycle automaton with thread-safe transitions | `ml/operations/state.py` |
| 2 | Valid transition table + operator force-override | `_TRANSITIONS` dict + `force_transition()` |
| 3 | Full audit history (every transition timestamped) | `get_history()` returns all events |
| 4 | Idempotent background scheduler with SHA-256 job ID | `ForecastScheduler` + `ForecastJob.make_job_id()` |
| 5 | Manual job submission with skip-on-duplicate | `submit_manual_job()` + `_completed` set |
| 6 | 8 built-in alert rules covering all failure modes | `BUILT_IN_RULES` in `alerts.py` |
| 7 | Alert lifecycle: raise -> acknowledge -> resolve | `evaluate()`, `acknowledge()`, `resolve()` |
| 8 | Feature drift (KS), prediction drift, regime drift | `DriftMonitor.compute_drift()` |
| 9 | Calibration ECE drift for all 4 IMD thresholds | 0.1 / 64.5 / 115.6 / 204.5 mm |
| 10 | 30-point readiness checklist across 6 categories | `ProductionReadinessEngine.evaluate()` |
| 11 | GO / CONDITIONAL_GO / NO_GO gate verdict | `overall_status` field |
| 12 | REAL_OPERATIONAL gate blocked in SYNTHETIC_DEMO | `gate_real_operational = False` |
| 13 | 15 REST API endpoints under `/api/operations/` | `ramp/api/v1/operations.py` |
| 14 | 5-tab Operations Control Center UI | `frontend/src/pages/Operations.tsx` |
| 15 | 44 tests passing, 0 regressions | `pytest tests/test_phase15_operations.py` |

---

## 3. Architecture

```
PHASE 15 - OPERATIONS CONTROL CENTER ARCHITECTURE

Frontend: /operations (React 5-Tab UI)
  Tab 1: Overview      -> State machine diagram + transition controls
  Tab 2: Scheduler     -> Start/Stop + job queue + manual submit
  Tab 3: Alerts        -> Active alerts + 8 rule definitions
  Tab 4: Drift Monitor -> KS, prediction, regime, ECE drift
  Tab 5: Readiness     -> 30-check GO/NO-GO checklist

REST API: /api/operations/ (15 endpoints, FastAPI)
  GET  /status            -> Full ops snapshot
  GET  /state             -> State + transition history
  POST /state/transition  -> Operator override
  GET  /scheduler         -> Scheduler status & config
  POST /scheduler/start   -> Start automated scheduler
  POST /scheduler/stop    -> Stop automated scheduler
  GET  /jobs              -> Recent forecast jobs
  GET  /jobs/{id}         -> Single job detail
  POST /jobs/submit       -> Manual job submission
  GET  /alerts            -> Active alert list + rules
  POST /alerts/{id}/acknowledge -> Operator acknowledgement
  POST /alerts/{id}/resolve     -> Alert resolution
  GET  /drift             -> Latest drift diagnostic report
  GET  /readiness         -> 30-point readiness checklist
  GET  /health            -> Compact health probe (LB-ready)

Backend: ml/operations/ (5 Python modules)
  state.py      -> OperationalStateMachine (11 states, thread-safe)
  scheduler.py  -> ForecastScheduler (idempotent, SHA-256 job IDs)
  alerts.py     -> AlertMonitor (8 rules, deduplicated lifecycle)
  drift.py      -> DriftMonitor (KS + prediction + regime + ECE)
  production.py -> ProductionReadinessEngine (30 checks, 6 categories)
```

---

## 4. State Machine Design

### 4.1 States

| State | Meaning |
|-------|---------|
| `INITIALIZING` | System startup; loading model registry |
| `WAITING_FOR_DATA` | Awaiting NWP cycle discovery |
| `DATA_RECEIVED` | NWP data located; pre-validation pending |
| `VALIDATING` | Running 11 automated validation gates |
| `VALIDATION_FAILED` | One or more gates failed; operator action required |
| `READY_FOR_INFERENCE` | All gates passed; inference may execute |
| `INFERENCING` | Pipeline executing (exclusive lock held) |
| `PUBLISHING` | Writing products to storage; provenance recording |
| `PUBLISHED` | Products committed; provenance recorded |
| `ALERT_RAISED` | Active alert requires operator acknowledgment |
| `CYCLE_COMPLETE` | Cycle archived; scheduler may restart |

### 4.2 Transition Policy

- **Normal transitions**: Validated against `_TRANSITIONS` adjacency table. Illegal transitions are silently rejected; state unchanged.
- **Force-transitions**: Operator overrides that bypass the guard, recorded in history with `triggered_by="OPERATOR"`.
- **Thread safety**: All reads and writes to `_state` and `_history` are protected by `threading.Lock`.
- **Listener hooks**: External monitors subscribe via `add_listener()` and receive `TransitionEvent` on every state change.

### 4.3 Transition Table

```
INITIALIZING        -> WAITING_FOR_DATA, ALERT_RAISED
WAITING_FOR_DATA    -> DATA_RECEIVED, ALERT_RAISED
DATA_RECEIVED       -> VALIDATING, ALERT_RAISED
VALIDATING          -> READY_FOR_INFERENCE, VALIDATION_FAILED, ALERT_RAISED
VALIDATION_FAILED   -> WAITING_FOR_DATA, ALERT_RAISED
READY_FOR_INFERENCE -> INFERENCING, ALERT_RAISED
INFERENCING         -> PUBLISHING, ALERT_RAISED
PUBLISHING          -> PUBLISHED, ALERT_RAISED
PUBLISHED           -> CYCLE_COMPLETE
ALERT_RAISED        -> WAITING_FOR_DATA
CYCLE_COMPLETE      -> WAITING_FOR_DATA
```

---

## 5. Scheduler Design

### 5.1 Idempotency Guarantee

Every forecast job is identified by a deterministic SHA-256 hash of `(cycle_id, lead_hours, model_version)`. The first 16 hex characters serve as the `job_id`. Completed job IDs go into `_completed: set[str]`. Re-submission of the same tuple returns `SKIPPED` status immediately without pipeline execution.

```python
job_id = hashlib.sha256(
    f"{cycle_id}:{lead_hours}:{model_version}".encode()
).hexdigest()[:16]
```

### 5.2 Background Polling

The automated scheduler runs in `threading.Thread(daemon=True)`, waking every `poll_interval_s` seconds (default 300 s). Each poll:
1. Calls `state_machine.transition(WAITING_FOR_DATA)`.
2. Discovers available demo cycles (`DEMO_<date>_<time>Z`).
3. Submits a job for each (cycle, lead) pair not already completed.
4. Increments `poll_count` and records `last_poll_at`.

---

## 6. Alert Monitor Design

### 6.1 Built-In Rules

| Rule ID | Name | Metric | Condition | Threshold | Severity |
|---------|------|--------|-----------|-----------|----------|
| RULE_001 | High Job Failure Rate | `job_failure_rate` | `>` | 0.20 | WARNING |
| RULE_002 | Consecutive Job Failures | `consecutive_failures` | `>=` | 3.0 | CRITICAL |
| RULE_003 | RMSE Drift Detected | `rmse_drift_pct` | `>` | 0.15 | WARNING |
| RULE_004 | Extreme ECE Degradation | `extreme_ece` | `>` | 0.08 | CRITICAL |
| RULE_005 | Scheduler Stall | `scheduler_stalled` | `>=` | 1.0 | CRITICAL |
| RULE_006 | Unauthorized Real Mode | `unauthorized_real_mode` | `>=` | 1.0 | CRITICAL |
| RULE_007 | Input Checksum Failure | `checksum_failures` | `>=` | 1.0 | CRITICAL |
| RULE_008 | Validation Gate Degradation | `validation_gate_failure_rate` | `>` | 0.10 | WARNING |

### 6.2 Alert Lifecycle

```
EVALUATE(metrics) -> new alerts with ACTIVE status
ACKNOWLEDGE(id)   -> alert.acknowledged = True, alert.acknowledged_by = operator
RESOLVE(id)       -> alert.resolved = True (removed from active list)
```

De-duplication: An active (unresolved) alert for a given rule cannot be raised twice. `evaluate()` checks `_active_by_rule` before creating a new alert.

---

## 7. Drift Monitor Design

### 7.1 Diagnostic Scope

> **Critical constraint**: Drift detection is **diagnostic only**. It never triggers model retraining, architecture changes, or training data updates. Any response action requires explicit human decision-making and a new formal training phase.

### 7.2 Drift Dimensions

| Dimension | Method | Coverage |
|-----------|--------|----------|
| Feature drift | Kolmogorov-Smirnov statistic | All 18 canonical predictors in `ramp_features_v1.0.0` |
| Prediction drift | Mean shift (absolute + percentage) | Full forecast distribution |
| Regime drift | Frequency shift per regime | All 7 canonical weather regimes |
| Calibration drift | ECE delta from baseline | 4 IMD thresholds (0.1, 64.5, 115.6, 204.5 mm) |

### 7.3 Drift Levels

| Level | KS Threshold | ECE Delta | Frequency Shift |
|-------|-------------|-----------|-----------------|
| NONE | < 0.10 | < 0.02 | < 0.10 |
| WARNING | 0.10-0.20 | 0.02-0.05 | 0.10-0.20 |
| CRITICAL | > 0.20 | > 0.05 | > 0.20 |

Overall drift level = maximum of all dimension drift levels.

---

## 8. Production Readiness Engine Design

### 8.1 30-Check Framework

| Category | Name | Checks |
|----------|------|--------|
| CAT-A | Model Registry Integrity | 5 -- artifact presence, checksums, calibration files, version metadata, training provenance |
| CAT-B | Data Infrastructure | 5 -- NWP source availability, data schema, preprocessing pipeline, IMD obs access, data version |
| CAT-C | Inference Pipeline | 5 -- feature computation, MoE gating, expert outputs, monotonicity enforcement, uncertainty quantification |
| CAT-D | Monitoring & Alerting | 5 -- alert rules enabled, drift monitoring active, scheduler configured, health probe, audit logging |
| CAT-E | Operational Interface | 5 -- API health, frontend availability, documentation links, export formats, provenance metadata |
| CAT-F | Documentation & Provenance | 5 -- phase reports present, data honesty banners, scientific integrity statement, operational SOP, MoES compliance |

### 8.2 Gate Logic

| Gate | Condition | Status in SYNTHETIC_DEMO |
|------|-----------|--------------------------|
| `REAL_OPERATIONAL` | Requires authoritative NCMRWF/IMD data mount | **BLOCKED** |
| `SYNTHETIC_DEMO` | Requires all pipeline components verified | **OPEN** |

### 8.3 Verdict Thresholds

| Verdict | Condition |
|---------|-----------|
| GO | All 30 checks PASS |
| CONDITIONAL_GO | >= 25 PASS, 0 FAIL (warnings acceptable) |
| NO_GO | Any FAIL or < 25 PASS |

---

## 9. REST API Reference

All endpoints mount under `/api/operations/` with prefix `settings.API_PREFIX`.

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/status` | Full operations snapshot |
| 2 | GET | `/state` | Current state + last 50 transition events |
| 3 | POST | `/state/transition` | Operator force-transition |
| 4 | GET | `/scheduler` | Scheduler status and config |
| 5 | POST | `/scheduler/start` | Start automated scheduler |
| 6 | POST | `/scheduler/stop` | Stop automated scheduler gracefully |
| 7 | GET | `/jobs` | Recent forecast jobs (default last 50) |
| 8 | GET | `/jobs/{job_id}` | Single job detail |
| 9 | POST | `/jobs/submit` | Manual job: `{cycle_id, lead_hours}` |
| 10 | GET | `/alerts` | Active alerts + rules |
| 11 | POST | `/alerts/{id}/acknowledge` | Acknowledge by operator |
| 12 | POST | `/alerts/{id}/resolve` | Resolve alert |
| 13 | GET | `/drift` | Latest drift diagnostic report |
| 14 | GET | `/readiness` | 30-point pre-launch readiness checklist |
| 15 | GET | `/health` | Compact health probe (LB-ready) |

---

## 10. File Manifest

| File | Type | Purpose |
|------|------|---------|
| `ml/operations/__init__.py` | Python | Package exports |
| `ml/operations/state.py` | Python | 11-state automaton (235 LOC) |
| `ml/operations/scheduler.py` | Python | Idempotent scheduler (~340 LOC) |
| `ml/operations/alerts.py` | Python | 8-rule alert monitor (~280 LOC) |
| `ml/operations/drift.py` | Python | Drift diagnostic engine (~310 LOC) |
| `ml/operations/production.py` | Python | 30-point readiness engine (~620 LOC) |
| `backend/src/ramp/api/v1/operations.py` | Python | 15 REST endpoints (240 LOC) |
| `backend/src/ramp/main.py` | Python | +2 lines: import + mount |
| `frontend/src/pages/Operations.tsx` | TypeScript/React | 5-tab UI (~730 LOC) |
| `frontend/src/App.tsx` | TypeScript | +2 lines: import + route |
| `frontend/src/components/layout/Shell.tsx` | TypeScript | +1 nav item |
| `frontend/src/api/client.ts` | TypeScript | +15 fetch functions |
| `tests/test_phase15_operations.py` | Python | 44 tests (340 LOC) |
| `docs/reports/PHASE_15_PROJECT_REPORT.md` | Markdown | This document |

---

## 11. Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\SIH26080
collected 44 items

TestStateMachine::test_state_machine_initial_state                PASSED
TestStateMachine::test_state_machine_valid_transition             PASSED
TestStateMachine::test_state_machine_invalid_transition_rejected  PASSED
TestStateMachine::test_state_machine_force_transition             PASSED
TestStateMachine::test_state_machine_history_recorded             PASSED
TestStateMachine::test_state_machine_thread_safety                PASSED
TestStateMachine::test_transition_table_complete                  PASSED
TestScheduler::test_scheduler_initializes                         PASSED
TestScheduler::test_scheduler_job_id_deterministic                PASSED
TestScheduler::test_scheduler_idempotency                         PASSED
TestScheduler::test_scheduler_status_api                          PASSED
TestScheduler::test_job_status_enum_values                        PASSED
TestAlertMonitor::test_alert_built_in_rules_count                 PASSED
TestAlertMonitor::test_alert_monitor_evaluates_metrics            PASSED
TestAlertMonitor::test_alert_monitor_no_duplicate_active_alerts   PASSED
TestAlertMonitor::test_alert_monitor_acknowledge                  PASSED
TestAlertMonitor::test_alert_monitor_resolve                      PASSED
TestAlertMonitor::test_alert_severity_hierarchy                   PASSED
TestAlertMonitor::test_alert_rule_004_ece_threshold               PASSED
TestAlertMonitor::test_alert_no_alerts_on_nominal_metrics         PASSED
TestDriftMonitor::test_drift_monitor_feature_drift                PASSED
TestDriftMonitor::test_drift_monitor_prediction_drift             PASSED
TestDriftMonitor::test_drift_monitor_calibration_drift            PASSED
TestDriftMonitor::test_drift_monitor_regime_drift                 PASSED
TestDriftMonitor::test_drift_overall_level                        PASSED
TestDriftMonitor::test_drift_disclaimer_present                   PASSED
TestDriftMonitor::test_drift_report_serializable                  PASSED
TestProductionReadiness::test_readiness_evaluates_30_checks       PASSED
TestProductionReadiness::test_readiness_cat_a_checks              PASSED
TestProductionReadiness::test_readiness_gate_logic                PASSED
TestProductionReadiness::test_readiness_synthetic_demo_gate       PASSED
TestProductionReadiness::test_readiness_overall_status_valid      PASSED
TestProductionReadiness::test_readiness_6_categories              PASSED
TestProductionReadiness::test_readiness_report_serializable       PASSED
TestProductionReadiness::test_readiness_disclaimer_present        PASSED
TestOperationsAPI::test_operations_api_status_endpoint            PASSED
TestOperationsAPI::test_operations_api_state_endpoint             PASSED
TestOperationsAPI::test_operations_api_scheduler_endpoint         PASSED
TestOperationsAPI::test_operations_api_alerts_endpoint            PASSED
TestOperationsAPI::test_operations_api_drift_endpoint             PASSED
TestOperationsAPI::test_operations_api_readiness_endpoint         PASSED
TestOperationsAPI::test_operations_api_health_endpoint            PASSED
TestOperationsAPI::test_operations_api_invalid_state_transition   PASSED
TestOperationsAPI::test_operations_api_jobs_endpoint              PASSED

======================= 44 passed, 12 warnings in 9.10s =======================
```

**Result: 44/44 passed | 0 failures | 0 regressions | 12 deprecation warnings (non-blocking)**

---

## 12. Scientific Integrity & Data Honesty

Phase 15 strictly enforces the project-wide **Absolute Scientific Integrity Rule**:

| Constraint | Implementation |
|-----------|----------------|
| No fabricated real forecast cycles | Scheduler only discovers `DEMO_*` cycles in `SYNTHETIC_DEMO` mode |
| REAL_OPERATIONAL gate blocked | `gate_real_operational = False` until authoritative data mounted |
| Data honesty banner | `DataBanner` component displayed on every `/operations` tab load |
| Drift detection is diagnostic only | `DriftMonitor.compute_drift()` disclaimer: diagnostic only -- no retraining |
| Readiness disclaimer present | `ProductionReadinessEngine` embeds engineering-only disclaimer |
| Provenance on all job records | Every `ForecastJob` includes `data_mode`, `model_version`, `created_at` |
| Alert rule RULE_006 | `unauthorized_real_mode >= 1.0` triggers CRITICAL alert |

---

## 13. Integration with Prior Phases

| Phase | Integration Point |
|-------|------------------|
| Phase 13 | Model Registry -- readiness CAT-A checks verify artifact existence and checksums |
| Phase 14 | Forecast engine -- scheduler submits jobs through Phase 14 inference; state machine governs INFERENCING -> PUBLISHING -> PUBLISHED flow |
| Phase 12 | Real dataset infrastructure -- readiness CAT-B checks verify NWP/IMD data availability |
| Phase 11 | Spatial products -- drift monitor uses Phase 11 district/state baselines for prediction distribution |
| Phases 1-10 | No direct integration; immutability preserved |

---

## 14. Cumulative Phase Status

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Project Scaffolding & Data Infrastructure | COMPLETE |
| 2 | Feature Engineering | COMPLETE |
| 3 | Weather Regime Classification | COMPLETE |
| 4 | RAMP Mixture-of-Experts Core | COMPLETE |
| 5 | Calibration & Uncertainty | COMPLETE |
| 6 | Extreme Rainfall Probability | COMPLETE |
| 7 | Spatial Processing & Aggregation | COMPLETE |
| 8 | Verification Framework | COMPLETE |
| 9 | Explainability (XAI) | COMPLETE |
| 10 | API & Frontend Scaffold | COMPLETE |
| 11 | Spatial Forecast Dashboard | COMPLETE |
| 12 | Real Paired Dataset Infrastructure | COMPLETE |
| 13 | Model Registry & Training Pipeline | COMPLETE |
| 14 | Operational Forecast Inference Engine | COMPLETE |
| **15** | **Operations Control Center** | **COMPLETE** |
| 16+ | Future phases | LOCKED (PART AU constraint) |

---

## 15. Conclusion

Phase 15 completes the **operational governance layer** of the RAMP system. The five interlocking subsystems -- state machine, scheduler, alert monitor, drift monitor, and readiness engine -- provide full lifecycle management from cycle discovery to product archival, with transparent audit trails, strict idempotency guarantees, and a robust data honesty framework.

The system is **production-ready in SYNTHETIC_DEMO mode** and fully architected for `REAL_OPERATIONAL` activation upon authoritative NCMRWF NCUM / IMD observation data mount. The 30-point readiness checklist provides a clear, evidence-based GO/NO-GO verdict to guide that transition.

**RAMP v2.0.0 | SIH26080 | MoES / NCMRWF | Phase 15 Complete.**
