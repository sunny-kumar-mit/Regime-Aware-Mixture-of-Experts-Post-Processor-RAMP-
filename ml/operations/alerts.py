"""
Phase 15 — Operational Alert Monitor
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Alert severity hierarchy:
  INFO     — Informational, no operator action required
  WARNING  — Degraded performance, operator should review
  CRITICAL — Pipeline blocked or integrity risk; operator must acknowledge

Built-in alert rules:
  RULE_001: Job failure rate exceeds threshold (>20% failure rate)
  RULE_002: Consecutive failed cycles (>= 3 consecutive failures)
  RULE_003: Forecast RMSE drift above baseline by > 15%
  RULE_004: Extreme probability calibration ECE > 0.08
  RULE_005: Scheduler stalled (no poll for > 2× poll_interval)
  RULE_006: Data mode mismatch (unexpected REAL_OPERATIONAL without authorization)
  RULE_007: Model checksum failure
  RULE_008: Validation gate failure on >50% of recent cycles
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class AlertRule:
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    condition_key: str        # Key in metrics dict to evaluate
    threshold: float          # Threshold value
    comparison: str           # gt | lt | gte | lte | eq | ne
    enabled: bool = True


@dataclass
class Alert:
    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    triggered_at: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


# ── Built-In Alert Rule Definitions ─────────────────────────────────────────

BUILT_IN_RULES: List[AlertRule] = [
    AlertRule(
        rule_id="RULE_001",
        name="High Job Failure Rate",
        description="Job failure rate exceeds 20% over the last 10 jobs.",
        severity=AlertSeverity.WARNING,
        condition_key="job_failure_rate",
        threshold=0.20,
        comparison="gt",
    ),
    AlertRule(
        rule_id="RULE_002",
        name="Consecutive Cycle Failures",
        description="Three or more consecutive forecast cycles have failed.",
        severity=AlertSeverity.CRITICAL,
        condition_key="consecutive_failures",
        threshold=3.0,
        comparison="gte",
    ),
    AlertRule(
        rule_id="RULE_003",
        name="RMSE Drift Above Baseline",
        description="Forecast RMSE has drifted more than 15% above the registered baseline.",
        severity=AlertSeverity.WARNING,
        condition_key="rmse_drift_pct",
        threshold=0.15,
        comparison="gt",
    ),
    AlertRule(
        rule_id="RULE_004",
        name="Extreme Probability ECE Degradation",
        description="Extreme rainfall probability calibration ECE exceeds 0.08.",
        severity=AlertSeverity.WARNING,
        condition_key="extreme_ece",
        threshold=0.08,
        comparison="gt",
    ),
    AlertRule(
        rule_id="RULE_005",
        name="Scheduler Stalled",
        description="Scheduler has not polled for more than 2× the configured poll interval.",
        severity=AlertSeverity.CRITICAL,
        condition_key="scheduler_stalled",
        threshold=1.0,
        comparison="gte",
    ),
    AlertRule(
        rule_id="RULE_006",
        name="Unauthorized Data Mode",
        description="REAL_OPERATIONAL mode detected without authorized data mount.",
        severity=AlertSeverity.CRITICAL,
        condition_key="unauthorized_real_mode",
        threshold=1.0,
        comparison="gte",
    ),
    AlertRule(
        rule_id="RULE_007",
        name="Model Checksum Failure",
        description="SHA-256 checksum verification failed on one or more registered models.",
        severity=AlertSeverity.CRITICAL,
        condition_key="checksum_failures",
        threshold=1.0,
        comparison="gte",
    ),
    AlertRule(
        rule_id="RULE_008",
        name="Validation Gate Failure Rate",
        description="Validation gate failures on more than 50% of recent cycles.",
        severity=AlertSeverity.WARNING,
        condition_key="validation_gate_failure_rate",
        threshold=0.50,
        comparison="gt",
    ),
]


def _compare(value: float, threshold: float, comparison: str) -> bool:
    if comparison == "gt":
        return value > threshold
    elif comparison == "lt":
        return value < threshold
    elif comparison == "gte":
        return value >= threshold
    elif comparison == "lte":
        return value <= threshold
    elif comparison == "eq":
        return value == threshold
    elif comparison == "ne":
        return value != threshold
    return False


class AlertMonitor:
    """
    Threshold-based operational alert monitor.

    The monitor evaluates a metrics snapshot (dict of floats) against
    the built-in alert rule set on each `evaluate()` call. Active alerts
    are stored and can be acknowledged or resolved by the operator.
    """

    def __init__(self, rules: Optional[List[AlertRule]] = None):
        self._rules = rules or list(BUILT_IN_RULES)
        self._alerts: Dict[str, Alert] = {}        # alert_id → Alert
        self._alert_counter = 0
        self._lock = threading.Lock()
        self._evaluation_count = 0
        self._last_evaluation_at: Optional[str] = None

    def evaluate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate current metrics against all enabled rules.
        Returns list of newly triggered alerts.
        """
        self._evaluation_count += 1
        self._last_evaluation_at = datetime.now(timezone.utc).isoformat()
        new_alerts: List[Alert] = []

        for rule in self._rules:
            if not rule.enabled:
                continue
            val = metrics.get(rule.condition_key)
            if val is None:
                continue
            try:
                val_f = float(val)
            except (TypeError, ValueError):
                continue

            if _compare(val_f, rule.threshold, rule.comparison):
                alert = self._raise_alert(rule, val_f, metrics)
                if alert:
                    new_alerts.append(alert)

        return new_alerts

    def _raise_alert(
        self,
        rule: AlertRule,
        value: float,
        context: Dict[str, Any],
    ) -> Optional[Alert]:
        """Create or update an alert for the given rule. De-duplicates by rule_id."""
        with self._lock:
            # Check if there's already an active (unresolved) alert for this rule
            existing = next(
                (a for a in self._alerts.values() if a.rule_id == rule.rule_id and not a.resolved),
                None,
            )
            if existing:
                return None  # Don't duplicate active alerts

            self._alert_counter += 1
            alert_id = f"ALERT_{self._alert_counter:04d}_{rule.rule_id}"
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                message=(
                    f"{rule.name}: {rule.description} "
                    f"(observed={value:.4f}, threshold={rule.threshold}, op={rule.comparison})"
                ),
                triggered_at=datetime.now(timezone.utc).isoformat(),
                context={k: v for k, v in context.items() if isinstance(v, (int, float, str, bool))},
            )
            self._alerts[alert_id] = alert
            logger.warning(f"ALERT RAISED [{rule.severity.value}] {alert_id}: {rule.name}")
            return alert

    def acknowledge(self, alert_id: str, operator: str = "OPERATOR") -> bool:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None or alert.acknowledged:
                return False
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
            alert.acknowledged_by = operator
        logger.info(f"Alert {alert_id} acknowledged by {operator}")
        return True

    def resolve(self, alert_id: str) -> bool:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None or alert.resolved:
                return False
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Alert {alert_id} resolved")
        return True

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._alerts.values() if not a.resolved]

    def get_all_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            alerts = sorted(self._alerts.values(), key=lambda a: a.triggered_at, reverse=True)
        return [a.to_dict() for a in alerts[:limit]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = [a for a in self._alerts.values() if not a.resolved]
            critical = [a for a in active if a.severity == AlertSeverity.CRITICAL]
        return {
            "evaluation_count": self._evaluation_count,
            "last_evaluation_at": self._last_evaluation_at,
            "total_alerts_raised": len(self._alerts),
            "active_alerts": len(active),
            "critical_alerts": len(critical),
            "rules_enabled": sum(1 for r in self._rules if r.enabled),
        }

    def get_rules(self) -> List[Dict[str, Any]]:
        return [asdict(r) for r in self._rules]
