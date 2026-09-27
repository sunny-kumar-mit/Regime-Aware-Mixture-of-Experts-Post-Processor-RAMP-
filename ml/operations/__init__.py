"""
Phase 15 — Operational Activation, Automated Forecast Scheduler,
Monitoring, Alerting & Production Readiness
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

This package provides:
  - OperationalStateMachine   : 8-state lifecycle state machine
  - ForecastScheduler         : Automated cycle scheduler with idempotency
  - ForecastJob               : Individual forecast job abstraction
  - AlertMonitor              : Threshold-based alert engine
  - DriftMonitor              : Model/data drift detection
  - ProductionReadinessEngine : Pre-launch readiness checklist
"""

from __future__ import annotations

from ml.operations.state import OperationalStateMachine, OperationalState
from ml.operations.scheduler import ForecastScheduler, ForecastJob, JobStatus
from ml.operations.alerts import AlertMonitor, AlertRule, Alert, AlertSeverity
from ml.operations.drift import DriftMonitor, DriftReport
from ml.operations.production import ProductionReadinessEngine, ReadinessCheckResult

__all__ = [
    "OperationalStateMachine",
    "OperationalState",
    "ForecastScheduler",
    "ForecastJob",
    "JobStatus",
    "AlertMonitor",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "DriftMonitor",
    "DriftReport",
    "ProductionReadinessEngine",
    "ReadinessCheckResult",
]
