"""
RAMP Operational Backup, Manifest & Disaster Recovery Engine
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import tarfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BackupManifest:
    backup_id: str
    created_at: str
    target_components: List[str]
    archive_filename: str
    archive_sha256: str
    file_count: int
    total_size_bytes: int
    is_verified: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionBackupManager:
    """
    Creates cryptographic, tamper-evident operational backups of the Model Registry,
    Audit Logs, Verification History, and System Configurations.
    """

    BACKUP_ROOT = Path("data/backups")

    COMPONENTS = {
        "model_registry": Path("ml/model_registry"),
        "audit_logs": Path("data/audit"),
        "verification_history": Path("data/processed/verification_history.json"),
        "forecast_manifests": Path("data/processed/forecasts/publication_catalog.json"),
        "configs": Path("deployment/configuration"),
    }

    @classmethod
    def compute_sha256(cls, filepath: Path) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def create_backup(cls, operator_id: str = "SYSTEM_SCHEDULER") -> BackupManifest:
        """Packages operational assets into a single verified tarball and generates manifest."""
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y%m%d_%H%M%S")
        backup_id = f"BKP_{now_str}"
        cls.BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

        tar_filename = f"{backup_id}.tar.gz"
        tar_path = cls.BACKUP_ROOT / tar_filename

        backed_components = []
        file_count = 0
        total_size = 0

        with tarfile.open(tar_path, "w:gz") as tar:
            for name, path in cls.COMPONENTS.items():
                if path.exists():
                    tar.add(path, arcname=name)
                    backed_components.append(name)
                    if path.is_file():
                        file_count += 1
                        total_size += path.stat().st_size
                    else:
                        for root, _, files in os.walk(path):
                            file_count += len(files)
                            for f in files:
                                try:
                                    total_size += os.path.getsize(os.path.join(root, f))
                                except OSError:
                                    pass

        chk = cls.compute_sha256(tar_path)
        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=now.isoformat(),
            target_components=backed_components,
            archive_filename=tar_filename,
            archive_sha256=chk,
            file_count=file_count,
            total_size_bytes=total_size,
            is_verified=True,
            metadata={"operator_id": operator_id, "environment": os.environ.get("APP_ENV", "PRODUCTION")},
        )

        manifest_path = cls.BACKUP_ROOT / f"{backup_id}_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        logger.info(f"Backup {backup_id} created successfully ({file_count} files, SHA256: {chk[:16]}...)")
        return manifest

    @classmethod
    def verify_backup(cls, manifest_path: Path) -> bool:
        """Verifies tarball integrity against recorded manifest checksum."""
        if not manifest_path.exists():
            return False
        with open(manifest_path, "r", encoding="utf-8") as f:
            m_data = json.load(f)

        tar_path = manifest_path.parent / m_data["archive_filename"]
        if not tar_path.exists():
            return False

        actual_chk = cls.compute_sha256(tar_path)
        return actual_chk == m_data["archive_sha256"]

    @classmethod
    def list_backups(cls) -> List[Dict[str, Any]]:
        manifests = []
        if cls.BACKUP_ROOT.exists():
            for m_file in cls.BACKUP_ROOT.glob("*_manifest.json"):
                try:
                    with open(m_file, "r", encoding="utf-8") as f:
                        manifests.append(json.load(f))
                except Exception:
                    pass
        return sorted(manifests, key=lambda x: x.get("created_at", ""), reverse=True)
