"""
RAMP Emergency Stop & Operational Circuit Breaker
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from ml.production.alerts import AlertSeverity, ProductionAlertCategory, ProductionAlertEngine
from ml.production.audit import ProductionAuditLogger, UserRole

logger = logging.getLogger(__name__)


@dataclass
class EmergencyStatus:
    is_emergency_active: bool
    triggered_at: Optional[str] = None
    triggered_by: Optional[str] = None
    reason: Optional[str] = None
    recovered_at: Optional[str] = None
    recovered_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmergencyShutdownManager:
    """
    Manages institutional emergency shutdown (EMERGENCY_STOP).
    Instantly halts job queuing and publication while preserving all audit and data state.
    """

    def __init__(self, alert_engine: Optional[ProductionAlertEngine] = None):
        self.alert_engine = alert_engine or ProductionAlertEngine()
        self.status = EmergencyStatus(is_emergency_active=False)

    def trigger_emergency_stop(self, actor: str, role: UserRole, reason: str) -> EmergencyStatus:
        """Triggers emergency stop. Requires OPERATOR, SUPERVISOR, or ADMIN."""
        if not ProductionAuditLogger.check_permission(role, UserRole.OPERATOR):
            raise PermissionError(f"Role {role.value} is not authorized to trigger emergency stop.")

        now_iso = datetime.now(timezone.utc).isoformat()
        self.status.is_emergency_active = True
        self.status.triggered_at = now_iso
        self.status.triggered_by = f"{actor} ({role.value})"
        self.status.reason = reason

        # Raise CRITICAL alert
        self.alert_engine.raise_alert(
            category=ProductionAlertCategory.SERVICE_UNAVAILABLE,
            severity=AlertSeverity.CRITICAL,
            title="EMERGENCY OPERATIONAL STOP ACTIVE",
            message=f"Emergency stop activated by {actor}: {reason}",
            source="EMERGENCY_SHUTDOWN",
        )

        # Log audit
        ProductionAuditLogger.log_action(
            actor=actor,
            role=role,
            action="EMERGENCY_STOP",
            resource="OPERATIONAL_SYSTEM",
            previous_state="NORMAL",
            new_state="EMERGENCY_STOPPED",
            reason=reason,
            status="SUCCESS",
        )

        logger.critical(f"EMERGENCY OPERATIONAL STOP TRIGGERED by {actor}: {reason}")
        return self.status

    def recover_from_emergency(self, actor: str, role: UserRole, justification: str) -> EmergencyStatus:
        """Recovers from emergency stop. Requires SUPERVISOR or ADMIN."""
        if not ProductionAuditLogger.check_permission(role, UserRole.SUPERVISOR):
            raise PermissionError(f"Role {role.value} cannot clear emergency stop. Requires SUPERVISOR or ADMIN.")

        if not self.status.is_emergency_active:
            return self.status

        now_iso = datetime.now(timezone.utc).isoformat()
        self.status.is_emergency_active = False
        self.status.recovered_at = now_iso
        self.status.recovered_by = f"{actor} ({role.value})"

        # Log audit
        ProductionAuditLogger.log_action(
            actor=actor,
            role=role,
            action="EMERGENCY_RECOVER",
            resource="OPERATIONAL_SYSTEM",
            previous_state="EMERGENCY_STOPPED",
            new_state="NORMAL",
            reason=justification,
            status="SUCCESS",
        )

        logger.info(f"EMERGENCY STOP CLEARED by {actor}: {justification}")
        return self.status

    def is_operational_blocked(self) -> bool:
        return self.status.is_emergency_active
