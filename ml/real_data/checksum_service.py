"""
RAMP Checksum & Integrity Service
SIH26080 | MoES / NCMRWF | Phase 19 Upgrade

Cryptographic SHA-256 computation, validation, and tamper detection for meteorological files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


class ChecksumService:
    """
    Computes and verifies cryptographic SHA-256 digests for meteorological files.
    """

    @staticmethod
    def compute_sha256(filepath: str | Path) -> str:
        path = Path(filepath)
        if not path.exists():
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def verify_sha256(cls, filepath: str | Path, expected_sha256: str) -> bool:
        actual = cls.compute_sha256(filepath)
        if not actual or not expected_sha256:
            return False
        return actual.lower() == expected_sha256.lower()
