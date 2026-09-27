"""
RAMP Role-Based Authorization & Immutable Production Audit Engine
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    VIEWER = "VIEWER"
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.VIEWER: 1,
    UserRole.OPERATOR: 2,
    UserRole.SUPERVISOR: 3,
    UserRole.ADMIN: 4,
}


@dataclass
class ProductionAuditRecord:
    audit_id: str
    timestamp: str
    actor: str
    role: str
    action: str
    resource: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: Optional[str] = None
    data_mode: str = "SYNTHETIC_DEMO"
    model_version: str = "v2.0.0"
    status: str = "SUCCESS"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionAuditLogger:
    """
    Records immutable operational events, state changes, job retries,
    publication retractions, and administrative commands to production_audit.jsonl.
    """

    AUDIT_FILE = Path("data/audit/production_audit.jsonl")

    @classmethod
    def check_permission(cls, user_role: UserRole, required_role: UserRole) -> bool:
        """Enforces hierarchical permission check."""
        return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    @classmethod
    def log_action(
        cls,
        actor: str,
        role: UserRole,
        action: str,
        resource: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        reason: Optional[str] = None,
        data_mode: str = "SYNTHETIC_DEMO",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ) -> ProductionAuditRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        audit_id = f"AUD_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}"

        rec = ProductionAuditRecord(
            audit_id=audit_id,
            timestamp=now_iso,
            actor=actor,
            role=role.value,
            action=action,
            resource=resource,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            data_mode=data_mode,
            model_version="v2.0.0",
            status=status,
            details=details or {},
        )

        cls.AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cls.AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to production audit log: {e}")

        return rec

    @classmethod
    def read_recent_logs(cls, limit: int = 50) -> List[Dict[str, Any]]:
        logs = []
        if cls.AUDIT_FILE.exists():
            try:
                with open(cls.AUDIT_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Error reading audit logs: {e}")
        return logs[-limit:]
