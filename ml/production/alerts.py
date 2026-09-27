"""
RAMP Production Alert Engine & Incident Lifecycle
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProductionAlertCategory(str, Enum):
    DATA_MISSING = "DATA_MISSING"
    DATA_STALE = "DATA_STALE"
    DATA_CORRUPT = "DATA_CORRUPT"
    DATA_QC_FAILURE = "DATA_QC_FAILURE"
    DATA_COVERAGE_LOW = "DATA_COVERAGE_LOW"
    CYCLE_MISSING = "CYCLE_MISSING"
    INFERENCE_FAILURE = "INFERENCE_FAILURE"
    PUBLICATION_FAILURE = "PUBLICATION_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    MODEL_INTEGRITY_FAILURE = "MODEL_INTEGRITY_FAILURE"
    SCHEDULER_STALL = "SCHEDULER_STALL"
    REAL_DATA_LOST = "REAL_DATA_LOST"
    UNAUTHORIZED_ACTIVATION = "UNAUTHORIZED_ACTIVATION"
    DISK_SPACE_LOW = "DISK_SPACE_LOW"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    RAISED = "RAISED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass
class ProductionAlertRecord:
    alert_id: str
    category: str
    severity: str
    title: str
    message: str
    source: str
    raised_at: str
    status: str = AlertStatus.RAISED.value
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionAlertEngine:
    """
    Evaluates institutional operational alerts, enforces de-duplication,
    and manages the raise -> acknowledge -> resolve lifecycle.
    """

    def __init__(self):
        self._alerts: Dict[str, ProductionAlertRecord] = {}

    def raise_alert(
        self,
        category: ProductionAlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProductionAlertRecord:
        """
        Raises a new alert or skips if an active (unresolved) alert with the
        same category and source already exists.
        """
        dedup_key = f"{category.value}_{source}"
        # Check active
        for a in self._alerts.values():
            if a.status in (AlertStatus.RAISED.value, AlertStatus.ACKNOWLEDGED.value):
                if a.category == category.value and a.source == source:
                    logger.debug(f"Alert {dedup_key} already active. Deduplicating.")
                    return a

        now_iso = datetime.now(timezone.utc).isoformat()
        alert_id = f"ALT_{category.value[:6]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        record = ProductionAlertRecord(
            alert_id=alert_id,
            category=category.value,
            severity=severity.value,
            title=title,
            message=message,
            source=source,
            raised_at=now_iso,
            status=AlertStatus.RAISED.value,
            metadata=metadata or {},
        )
        self._alerts[alert_id] = record
        logger.warning(f"PRODUCTION ALERT RAISED [{severity.value}]: {title} ({source})")
        return record

    def acknowledge_alert(self, alert_id: str, operator_id: str) -> ProductionAlertRecord:
        if alert_id not in self._alerts:
            raise KeyError(f"Alert {alert_id} not found.")
        alert = self._alerts[alert_id]
        if alert.status == AlertStatus.RESOLVED.value:
            raise ValueError(f"Alert {alert_id} is already resolved.")
        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
        alert.acknowledged_by = operator_id
        return alert

    def resolve_alert(self, alert_id: str, operator_id: str) -> ProductionAlertRecord:
        if alert_id not in self._alerts:
            raise KeyError(f"Alert {alert_id} not found.")
        alert = self._alerts[alert_id]
        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = datetime.now(timezone.utc).isoformat()
        alert.resolved_by = operator_id
        return alert

    def list_alerts(self, active_only: bool = False) -> List[ProductionAlertRecord]:
        if active_only:
            return [
                a for a in self._alerts.values()
                if a.status in (AlertStatus.RAISED.value, AlertStatus.ACKNOWLEDGED.value)
            ]
        return list(self._alerts.values())

    def get_alert(self, alert_id: str) -> Optional[ProductionAlertRecord]:
        return self._alerts.get(alert_id)
