"""
RAMP Authoritative Source Registry & Dynamic Operational State Tracker
SIH26080 | Phase 16 — Real-Data Activation & Operational Ingestion
MoES / NCMRWF

PART B — Source Registry Requirements:
  - Authoritative source registry tracking:
      source_id, provider, model, dataset_type, resolution,
      variables, units, expected_format, root_path, authority_level, enabled, status.
  - Dynamic discovery from filesystem (never hardcoded operational status).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.ingestion.sources import (
    AUTHORITATIVE_SOURCE_CONTRACTS,
    AuthorityLevel,
    DatasetType,
    SECONDARY_SOURCE_CONTRACTS,
    SourceContract,
    SourceStatus,
)

logger = logging.getLogger(__name__)


class SourceRegistry:
    """
    Authoritative operational catalog and state tracker for all meteorological data sources.
    """

    def __init__(self):
        # Initialize internal copy of registered contracts
        self._sources: Dict[str, SourceContract] = {
            k: SourceContract(**asdict(v)) for k, v in AUTHORITATIVE_SOURCE_CONTRACTS.items()
        }
        # Add secondary proxy contracts (disabled by default)
        for k, v in SECONDARY_SOURCE_CONTRACTS.items():
            self._sources[k] = SourceContract(**asdict(v))

        # Perform initial dynamic scan
        self.refresh_availability()

    def get_source(self, source_id: str) -> Optional[SourceContract]:
        """Lookup source by source_id."""
        return self._sources.get(source_id)

    def list_sources(self, enabled_only: bool = False) -> List[SourceContract]:
        """List registered sources."""
        sources = list(self._sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sources

    def list_authoritative_sources(self) -> List[SourceContract]:
        """List only authoritative primary sources."""
        return [
            s for s in self._sources.values()
            if s.authority_level == AuthorityLevel.AUTHORITATIVE_PRIMARY
        ]

    def refresh_availability(self) -> Dict[str, SourceStatus]:
        """
        Dynamically discovers availability from the filesystem.
        Never hardcodes availability status.
        """
        statuses = {}
        for source_id, contract in self._sources.items():
            root = Path(contract.root_path)
            if not root.exists():
                contract.status = SourceStatus.UNAVAILABLE
            else:
                # Check if any matching format files exist
                valid_files = []
                for ext in contract.expected_format:
                    valid_files.extend(list(root.glob(f"*{ext}")))
                    valid_files.extend(list(root.glob(f"*/*{ext}")))

                if not valid_files:
                    contract.status = SourceStatus.UNAVAILABLE
                else:
                    # Filter out test fixtures from counting as authoritative
                    real_files = [f for f in valid_files if "fixture" not in str(f).lower() and "synthetic" not in str(f).lower()]
                    if real_files:
                        contract.status = SourceStatus.DETECTED
                    else:
                        contract.status = SourceStatus.UNAVAILABLE

            statuses[source_id] = contract.status

        return statuses

    def update_source_status(self, source_id: str, new_status: SourceStatus) -> bool:
        """Updates runtime status of a registered source."""
        if source_id in self._sources:
            self._sources[source_id].status = new_status
            return True
        return False
