"""
RAMP Storage Monitor & Operational Retention Governance
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DirectoryStorageMetric:
    name: str
    path: str
    exists: bool
    total_bytes: int
    file_count: int
    retention_policy: str
    auto_delete_allowed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StorageMetrics:
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_percent_used: float
    status: str  # NORMAL | WARNING | CRITICAL
    directories: Dict[str, DirectoryStorageMetric]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["directories"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.directories.items()}
        return d


class OperationalStorageMonitor:
    """
    Monitors storage utilization across forecast products, raw archives,
    audit trails, and runtime logs. Enforces institutional retention rules.
    """

    WARNING_THRESHOLD_PERCENT = 85.0
    CRITICAL_THRESHOLD_PERCENT = 95.0

    MONITORED_PATHS: Dict[str, Dict[str, Any]] = {
        "raw_ncmrwf": {
            "path": "data/ncmrwf",
            "policy": "PERMANENT_ARCHIVE",
            "auto_delete_allowed": False,
        },
        "raw_imd": {
            "path": "data/imd",
            "policy": "PERMANENT_ARCHIVE",
            "auto_delete_allowed": False,
        },
        "processed_forecasts": {
            "path": "data/processed/forecasts",
            "policy": "ONLINE_90_DAYS_COLD_ARCHIVE",
            "auto_delete_allowed": False,
        },
        "audit_logs": {
            "path": "data/audit",
            "policy": "IMMUTABLE_NEVER_DELETE",
            "auto_delete_allowed": False,
        },
        "application_logs": {
            "path": "data/logs",
            "policy": "ROTATE_30_DAYS",
            "auto_delete_allowed": True,
        },
        "temp_storage": {
            "path": "data/temp",
            "policy": "PURGE_24_HOURS",
            "auto_delete_allowed": True,
        },
    }

    @classmethod
    def get_storage_metrics(cls) -> StorageMetrics:
        now_iso = datetime.now(timezone.utc).isoformat()
        root_path = Path(".").resolve()

        # System disk stats
        total, used, free = shutil.disk_usage(root_path)
        percent_used = round((used / total) * 100.0, 2) if total > 0 else 0.0

        if percent_used >= cls.CRITICAL_THRESHOLD_PERCENT:
            status = "CRITICAL"
        elif percent_used >= cls.WARNING_THRESHOLD_PERCENT:
            status = "WARNING"
        else:
            status = "NORMAL"

        dir_metrics: Dict[str, DirectoryStorageMetric] = {}
        for key, conf in cls.MONITORED_PATHS.items():
            p = Path(conf["path"])
            exists = p.exists()
            t_bytes = 0
            count = 0
            if exists:
                for root, _, files in os.walk(p):
                    count += len(files)
                    for f in files:
                        try:
                            t_bytes += os.path.getsize(os.path.join(root, f))
                        except (OSError, FileNotFoundError):
                            pass

            dir_metrics[key] = DirectoryStorageMetric(
                name=key,
                path=conf["path"],
                exists=exists,
                total_bytes=t_bytes,
                file_count=count,
                retention_policy=conf["policy"],
                auto_delete_allowed=conf["auto_delete_allowed"],
            )

        return StorageMetrics(
            disk_total_bytes=total,
            disk_used_bytes=used,
            disk_free_bytes=free,
            disk_percent_used=percent_used,
            status=status,
            directories=dir_metrics,
            timestamp=now_iso,
        )

    @classmethod
    def enforce_retention_rules(cls) -> Dict[str, int]:
        """
        Runs retention cleanup ONLY on directories explicitly tagged as auto_delete_allowed.
        Guarantees that audit logs and raw authoritative archives are never deleted.
        """
        cleaned: Dict[str, int] = {"temp_files_removed": 0, "logs_rotated": 0}
        temp_p = Path("data/temp")
        if temp_p.exists():
            for f in temp_p.glob("*"):
                if f.is_file():
                    try:
                        f.unlink()
                        cleaned["temp_files_removed"] += 1
                    except OSError:
                        pass
        return cleaned
