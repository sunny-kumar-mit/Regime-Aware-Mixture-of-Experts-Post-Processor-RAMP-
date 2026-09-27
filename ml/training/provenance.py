"""
RAMP Training Provenance and System Telemetry
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part U: Captures exact software, hardware, and runtime environment for complete auditability.
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def get_git_commit() -> Optional[str]:
    """Retrieve current Git commit SHA if in a repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def get_library_versions() -> Dict[str, str]:
    """Capture runtime versions of scientific packages."""
    versions = {"python": sys.version.split()[0]}
    for pkg in ["numpy", "pandas", "scipy", "sklearn", "lightgbm", "pydantic", "fastapi"]:
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not_installed"
    return versions


def get_system_hardware() -> Dict[str, Any]:
    """Capture CPU architecture, OS, and platform information."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
    }


def compute_bytes_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hash."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
