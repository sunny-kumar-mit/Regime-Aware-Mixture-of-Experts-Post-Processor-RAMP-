"""
RAMP Storage Migration Utility: MinIO / Local Vault to PostgreSQL + PostGIS
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Safely migrates all stored raw meteorological objects from MinIO / local vault into
PostgreSQL chunked storage (file_objects and file_chunks tables).

Safety invariants:
  1. Computes SHA-256 checksum before and after migration.
  2. Uploads data in chunks without buffering huge files in memory.
  3. Verifies post-insert checksum by reading back from PostgreSQL.
  4. Non-destructive: Does NOT delete source data until explicit confirmation.
  5. Records verifiable audit log in data/real/vault/migration_report.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure python path includes root and backend/src
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from backend.src.ramp.storage.connection import DatabaseManager
from backend.src.ramp.storage.postgres_storage import PostgresStorageProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ramp.migrate")


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_migration(vault_dir: Path, dry_run: bool = False) -> Dict[str, Any]:
    logger.info("==================================================================")
    logger.info("RAMP STORAGE MIGRATION: MinIO / Data Vault -> PostgreSQL + PostGIS")
    logger.info("==================================================================")
    logger.info(f"Source Vault Directory: {vault_dir}")
    logger.info(f"Dry Run: {dry_run}")

    db = DatabaseManager.get_instance()
    db.init_schema()
    storage = PostgresStorageProvider(db)

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vault_source": str(vault_dir),
        "dry_run": dry_run,
        "database_backend": db.check_health()["backend"],
        "total_files_scanned": 0,
        "migrated_successfully": 0,
        "verification_failures": 0,
        "skipped": 0,
        "items": [],
    }

    if not vault_dir.exists():
        logger.warning(f"Source directory {vault_dir} does not exist.")
        return report

    # Scan for files in objects dir
    files_to_migrate = [p for p in vault_dir.rglob("*") if p.is_file() and not p.name.endswith(".json")]
    report["total_files_scanned"] = len(files_to_migrate)
    logger.info(f"Found {len(files_to_migrate)} candidate files to migrate.")

    for fpath in files_to_migrate:
        file_id = fpath.stem
        filename = fpath.name
        size_bytes = fpath.stat().st_size
        sha256_pre = compute_file_sha256(fpath)

        logger.info(f"Processing: {filename} ({size_bytes} bytes, SHA-256={sha256_pre[:10]}...)")

        if dry_run:
            report["items"].append({
                "file_id": file_id,
                "filename": filename,
                "size_bytes": size_bytes,
                "sha256": sha256_pre,
                "status": "DRY_RUN_CHECKED",
            })
            continue

        try:
            # 1. Upload in chunks
            with open(fpath, "rb") as stream_data:
                upload_meta = storage.upload(
                    file_id=file_id,
                    filename=filename,
                    data=stream_data,
                    chunk_size=1024 * 1024,
                    metadata={"original_path": str(fpath), "migration_source": "MINIO_VAULT"},
                )

            # 2. Verify post-insert checksum by reading back
            downloaded = storage.download(file_id)
            sha256_post = hashlib.sha256(downloaded).hexdigest()

            if sha256_post != sha256_pre:
                logger.error(f"VERIFICATION FAILED for {filename}: pre={sha256_pre}, post={sha256_post}")
                report["verification_failures"] += 1
                report["items"].append({
                    "file_id": file_id,
                    "filename": filename,
                    "status": "CHECKSUM_MISMATCH",
                    "expected": sha256_pre,
                    "actual": sha256_post,
                })
            else:
                logger.info(f"SUCCESS: {filename} verified in PostgreSQL storage.")
                report["migrated_successfully"] += 1
                report["items"].append({
                    "file_id": file_id,
                    "filename": filename,
                    "size_bytes": size_bytes,
                    "sha256": sha256_post,
                    "chunks": upload_meta["chunks_count"],
                    "status": "MIGRATED_AND_VERIFIED",
                })

        except Exception as e:
            logger.error(f"Migration error on {filename}: {e}")
            report["verification_failures"] += 1
            report["items"].append({
                "file_id": file_id,
                "filename": filename,
                "status": "ERROR",
                "error": str(e),
            })

    # Save report
    out_dir = Path("data/real/vault")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "migration_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("==================================================================")
    logger.info(
        f"MIGRATION COMPLETE: {report['migrated_successfully']}/{report['total_files_scanned']} "
        f"migrated successfully. Report written to {report_file}"
    )
    logger.info("==================================================================")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MinIO / local vault to PostgreSQL + PostGIS")
    parser.add_argument(
        "--source-dir",
        default="data/real/vault/objects",
        help="Source directory containing raw vault files",
    )
    parser.add_argument("--dry-run", action="store_true", help="Scan and verify without writing to DB")
    args = parser.parse_args()

    run_migration(Path(args.source_dir), dry_run=args.dry_run)
