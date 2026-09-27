"""
Forecast Cycle & Lead Time Resolution Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part C & D: Resolves forecast cycles (00Z, 06Z, 12Z, 18Z) and dynamic lead times.
Never fabricates real cycles. Provides deterministic demo cycles when real data are unmounted.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ramp.data_plane.discovery import DataDiscoveryService
from ramp.data_plane.cycle import ForecastCycle, LeadTimeNormalizer
from ramp.data_plane.sources import DataMode

logger = logging.getLogger(__name__)

STANDARD_DEMO_LEADS = [6, 12, 18, 24, 36, 48, 72, 96, 120]


@dataclass
class ResolvedCycleInfo:
    cycle_id: str
    date: str
    cycle_utc: str
    model: str
    provider_id: str
    initialization_time: str
    available_leads: List[int]
    status: str
    data_mode: str
    is_real: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForecastCycleResolver:
    """
    Discovers available forecast cycles from disk.
    If real operational data are unmounted, generates deterministic demo cycles
    clearly labeled as SYNTHETIC_DEMO without pretending to be real NCMRWF cycles.
    """

    def __init__(self):
        self.discovery = DataDiscoveryService()

    def list_available_cycles(self) -> List[ResolvedCycleInfo]:
        """
        Scan operational directories. If real cycles exist, return them.
        Otherwise, provide deterministic demonstration cycles.
        """
        real_cycles: List[ResolvedCycleInfo] = []
        # Check NCUM / NEPS providers
        scans = self.discovery.scan_all()
        for p_res in scans.values():
            if p_res.data_mode in ("REAL_OPERATIONAL", "REAL_ARCHIVE") and p_res.available_cycles:
                for c in p_res.available_cycles:
                    real_cycles.append(
                        ResolvedCycleInfo(
                            cycle_id=c.cycle_id,
                            date=c.date,
                            cycle_utc=c.cycle_utc,
                            model=c.model,
                            provider_id=c.provider_id,
                            initialization_time=c.initialization_time,
                            available_leads=c.available_leads,
                            status=c.status,
                            data_mode=c.data_mode,
                            is_real=True,
                        )
                    )

        if real_cycles:
            return sorted(real_cycles, key=lambda x: x.initialization_time, reverse=True)

        # Scientific Honesty: Return deterministic DEMO cycles
        demo_date = "2026-09-27"
        demo_cycles = [
            ResolvedCycleInfo(
                cycle_id="DEMO_20260927_00Z",
                date=demo_date,
                cycle_utc="00 UTC",
                model="NCUM_SYNTHETIC_DEMO",
                provider_id="synthetic_demo",
                initialization_time=f"{demo_date}T00:00:00Z",
                available_leads=STANDARD_DEMO_LEADS,
                status="DEMO_AVAILABLE",
                data_mode="SYNTHETIC_DEMO",
                is_real=False,
            ),
            ResolvedCycleInfo(
                cycle_id="DEMO_20260927_12Z",
                date=demo_date,
                cycle_utc="12 UTC",
                model="NCUM_SYNTHETIC_DEMO",
                provider_id="synthetic_demo",
                initialization_time=f"{demo_date}T12:00:00Z",
                available_leads=[6, 12, 18, 24, 48],
                status="DEMO_AVAILABLE",
                data_mode="SYNTHETIC_DEMO",
                is_real=False,
            ),
        ]
        return demo_cycles

    def get_cycle(self, cycle_id: str) -> Optional[ResolvedCycleInfo]:
        cycles = self.list_available_cycles()
        for c in cycles:
            if c.cycle_id == cycle_id:
                return c
        return None

    def resolve_valid_time(self, cycle: ResolvedCycleInfo, lead_hours: int) -> str:
        """Calculate forecast valid time: init_time + lead_time."""
        init_dt = datetime.fromisoformat(cycle.initialization_time.replace("Z", "+00:00"))
        import datetime as dt_module
        valid_dt = init_dt + dt_module.timedelta(hours=lead_hours)
        return valid_dt.strftime("%Y-%m-%d %H:%M UTC")
