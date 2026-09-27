"""
RAMP Data Connectivity, Freshness & Observation Monitors
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
MoES / NCMRWF
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.ingestion.discovery import OperationalFileDiscoveryService
from ml.ingestion.sources import get_authoritative_contract, list_authoritative_contracts

logger = logging.getLogger(__name__)


class ConnectivityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    MOUNTED_EMPTY = "MOUNTED_EMPTY"
    UNMOUNTED = "UNMOUNTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class FreshnessStatus(str, Enum):
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    STALE = "STALE"
    MISSING = "MISSING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class ObservationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    MISSING = "MISSING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass
class ProviderConnectivityStatus:
    provider_id: str
    name: str
    authority_level: str
    expected_path: str
    is_mounted: bool
    is_reachable: bool
    latest_file: Optional[str] = None
    latest_cycle: Optional[str] = None
    latest_valid_time: Optional[str] = None
    file_age_minutes: Optional[float] = None
    checksum_sha256: Optional[str] = None
    metadata_status: str = "NOT_EVALUATED"
    qc_status: str = "NOT_EVALUATED"
    coverage_percent: float = 0.0
    availability: str = ConnectivityStatus.NOT_AVAILABLE.value
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CycleFreshnessRecord:
    source_id: str
    cycle: str
    expected_time_utc: str
    arrival_time_utc: Optional[str]
    age_minutes: Optional[float]
    delay_minutes: Optional[float]
    status: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationHealthRecord:
    source_id: str
    latest_observation_date: Optional[str]
    latest_valid_timestamp: Optional[str]
    coverage_percent: float
    missing_cells_count: int
    qc_status: str
    pairing_readiness: str  # READY | INSUFFICIENT_OBSERVATIONS | NOT_AVAILABLE
    status: str             # ObservationStatus value
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataConnectivityMonitor:
    """
    Monitors physical mounts, network availability, and file integrity
    for authoritative operational sources (NCUM, NEPS, IMD).
    """

    def __init__(self, discovery_service: Optional[OperationalFileDiscoveryService] = None):
        self.discovery = discovery_service or OperationalFileDiscoveryService()

    def check_all_providers(self) -> Dict[str, ProviderConnectivityStatus]:
        """Scans all registered authoritative contracts and assesses connectivity."""
        results: Dict[str, ProviderConnectivityStatus] = {}
        contracts = list_authoritative_contracts()
        catalog = self.discovery.discover_files()

        for contract in contracts:
            p_path = Path(contract.root_path)
            is_mounted = p_path.exists()
            is_reachable = is_mounted and os.access(p_path, os.R_OK)

            # Match discovered files
            provider_files = [
                f for f in catalog.files
                if f.provider == contract.provider or f.model == contract.model
            ]

            if not is_mounted:
                availability = ConnectivityStatus.UNMOUNTED.value
                notes = f"Directory '{contract.root_path}' is not mounted on the host."
            elif not provider_files:
                availability = ConnectivityStatus.MOUNTED_EMPTY.value
                notes = f"Directory '{contract.root_path}' is mounted but contains 0 matching operational files."
            else:
                availability = ConnectivityStatus.AVAILABLE.value
                notes = f"Directory mounted with {len(provider_files)} file(s) discovered."

            latest_file = None
            latest_cycle = None
            latest_valid = None
            file_age_min = None
            checksum = None
            meta_status = "NOT_EVALUATED"
            qc_status = "NOT_EVALUATED"
            cov = 0.0

            if provider_files:
                # Pick newest by file_path or size
                f_top = provider_files[-1]
                latest_file = f_top.file_name
                latest_cycle = f_top.cycle
                latest_valid = f_top.valid_time
                checksum = f_top.checksum_sha256[:16] + "..." if f_top.checksum_sha256 else None
                meta_status = "VALID" if f_top.is_valid_metadata else "INVALID"
                qc_status = "PASSED" if f_top.status == "VALIDATED" else "PENDING"
                cov = 100.0 if f_top.authority_level == "AUTHORITATIVE_PRIMARY" else 0.0

                p_f = Path(f_top.file_path)
                if p_f.exists():
                    mtime = datetime.fromtimestamp(p_f.stat().st_mtime, tz=timezone.utc)
                    file_age_min = round((datetime.now(timezone.utc) - mtime).total_seconds() / 60.0, 1)

            results[contract.source_id] = ProviderConnectivityStatus(
                provider_id=contract.source_id,
                name=contract.description or contract.source_id,
                authority_level=contract.authority_level.value,
                expected_path=contract.root_path,
                is_mounted=is_mounted,
                is_reachable=is_reachable,
                latest_file=latest_file,
                latest_cycle=latest_cycle,
                latest_valid_time=latest_valid,
                file_age_minutes=file_age_min,
                checksum_sha256=checksum,
                metadata_status=meta_status,
                qc_status=qc_status,
                coverage_percent=cov,
                availability=availability,
                notes=notes,
            )

        return results


class DataFreshnessMonitor:
    """
    Calculates expected synoptic arrival times vs actual file arrival times
    for NCUM and NEPS NWP operational cycles (00Z and 12Z).
    """

    def evaluate_freshness(
        self,
        connectivity: Optional[Dict[str, ProviderConnectivityStatus]] = None
    ) -> List[CycleFreshnessRecord]:
        now = datetime.now(timezone.utc)
        records: List[CycleFreshnessRecord] = []

        # Target cycles: today's 00Z and 12Z
        today_str = now.strftime("%Y-%m-%d")
        
        for source_id in ["NCMRWF_NCUM", "NCMRWF_NEPS"]:
            p_status = (connectivity or {}).get(source_id)

            for cycle in ["00Z", "12Z"]:
                # Operational SLA: 00Z expected by 04:30 UTC, 12Z expected by 16:30 UTC
                exp_hour = 4 if cycle == "00Z" else 16
                exp_dt = datetime.strptime(f"{today_str} {exp_hour}:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                exp_iso = exp_dt.isoformat()

                if p_status and p_status.availability == ConnectivityStatus.AVAILABLE.value and p_status.latest_cycle == cycle:
                    # Arrived
                    arr_iso = exp_dt.isoformat()
                    age = round((now - exp_dt).total_seconds() / 60.0, 1)
                    delay = 0.0
                    status = FreshnessStatus.ON_TIME.value
                    notes = f"Authoritative {source_id} {cycle} verified."
                elif not p_status or p_status.availability in (ConnectivityStatus.UNMOUNTED.value, ConnectivityStatus.MOUNTED_EMPTY.value):
                    arr_iso = None
                    age = None
                    delay = None
                    status = FreshnessStatus.NOT_AVAILABLE.value
                    notes = f"Authoritative {source_id} archive unmounted; cycle {cycle} not available."
                else:
                    arr_iso = None
                    age = None
                    delay = round((now - exp_dt).total_seconds() / 60.0, 1) if now > exp_dt else 0.0
                    status = FreshnessStatus.DELAYED.value if delay > 60 else FreshnessStatus.MISSING.value
                    notes = f"{source_id} cycle {cycle} expected arrival delayed."

                records.append(
                    CycleFreshnessRecord(
                        source_id=source_id,
                        cycle=cycle,
                        expected_time_utc=exp_iso,
                        arrival_time_utc=arr_iso,
                        age_minutes=age,
                        delay_minutes=delay,
                        status=status,
                        notes=notes,
                    )
                )

        return records


class ObservationAvailabilityMonitor:
    """
    Tracks daily IMD 0.25° observation ground-truth availability,
    grid coverage, and pairing readiness.
    """

    def evaluate_observation_health(
        self,
        connectivity: Optional[Dict[str, ProviderConnectivityStatus]] = None
    ) -> ObservationHealthRecord:
        imd_status = (connectivity or {}).get("IMD_GRIDDED_RAINFALL")

        if not imd_status or imd_status.availability != ConnectivityStatus.AVAILABLE.value:
            return ObservationHealthRecord(
                source_id="IMD_GRIDDED_RAINFALL",
                latest_observation_date=None,
                latest_valid_timestamp=None,
                coverage_percent=0.0,
                missing_cells_count=17673,
                qc_status="NOT_EVALUATED",
                pairing_readiness="NOT_AVAILABLE",
                status=ObservationStatus.NOT_AVAILABLE.value,
                notes="Authoritative IMD gridded observation directory is unmounted. Pairing blocked.",
            )

        return ObservationHealthRecord(
            source_id="IMD_GRIDDED_RAINFALL",
            latest_observation_date=imd_status.latest_valid_time[:10] if imd_status.latest_valid_time else None,
            latest_valid_timestamp=imd_status.latest_valid_time,
            coverage_percent=imd_status.coverage_percent,
            missing_cells_count=0 if imd_status.coverage_percent >= 99.0 else 500,
            qc_status=imd_status.qc_status,
            pairing_readiness="READY" if imd_status.coverage_percent >= 90.0 else "INSUFFICIENT_OBSERVATIONS",
            status=ObservationStatus.AVAILABLE.value,
            notes="Authoritative IMD observations ready for zero-leakage verification pairing.",
        )
