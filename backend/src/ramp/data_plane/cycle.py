"""
RAMP Forecast Cycle Model & Lead Time Discovery
SIH26080 | Phase 11 — Real Data Activation & Operational Data Plane
MoES / NCMRWF

Complies with Sections 4 & 5 of Phase 11:
- First-class ForecastCycle object (date, cycle_utc, model, initialization_time, available_leads, status).
- Supported cycles: 00 UTC, 06 UTC, 12 UTC, 18 UTC.
- Only exposes cycles actually present in filesystem. Never fabricates cycles.
- Arbitrary lead times discovered dynamically from actual files (e.g. 6h, 12h, 18h, 24h ... 120h+).
- Normalizes lead times cleanly into hours and human-readable tags.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


VALID_CYCLES = ["00 UTC", "06 UTC", "12 UTC", "18 UTC"]
CYCLE_HOURS = {0: "00 UTC", 6: "06 UTC", 12: "12 UTC", 18: "18 UTC"}
HOUR_FROM_CYCLE = {"00 UTC": 0, "06 UTC": 6, "12 UTC": 12, "18 UTC": 18, "00Z": 0, "06Z": 6, "12Z": 12, "18Z": 18}


@dataclass
class ForecastCycle:
    """
    First-class representation of an atmospheric NWP operational model run.
    """
    cycle_id: str                   # e.g. "NCUM_20260715_00Z"
    date: str                       # YYYY-MM-DD
    cycle_utc: str                  # "00 UTC", "06 UTC", "12 UTC", or "18 UTC"
    cycle_hour: int                 # 0, 6, 12, or 18
    model: str                      # "NCUM", "NEPS", "GFS", "GEFS", or "SYNTHETIC_DEMO"
    provider_id: str                # "ncmrwf_ncum", "gfs", etc.
    initialization_time: str        # ISO 8601 UTC
    available_leads: List[int]      # Discovered from actual files, e.g. [6, 12, 18, 24, 48, 72, ...]
    status: str                     # "COMPLETE", "PARTIAL", "AVAILABLE", "EMPTY"
    files: List[str] = field(default_factory=list)
    file_hashes: Dict[str, str] = field(default_factory=dict)
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def lead_tags(self) -> List[str]:
        return [f"{h}h" for h in sorted(self.available_leads)]


class LeadTimeNormalizer:
    """
    Normalizes arbitrary lead times into integer hours and standard step tags.
    Does NOT hardcode [24, 48, 72, 96, 120].
    """

    @staticmethod
    def extract_lead_from_filename(filename: str) -> Optional[int]:
        """
        Parses lead times from patterns like:
          _f024.nc -> 24
          _lead48.nc -> 48
          _072h.nc -> 72
          _f120.grib2 -> 120
        """
        patterns = [
            r"_f(\d{2,3})\.",
            r"_lead(\d{1,3})\.",
            r"_(\d{1,3})h\.",
            r"_(\d{1,3})hr\.",
            r"_step(\d{1,3})\.",
            r"_f(\d{2,3})_",
        ]
        for p in patterns:
            m = re.search(p, filename, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
        return None

    @staticmethod
    def format_lead_tag(lead_hours: int) -> str:
        return f"{lead_hours}h"


class CycleManager:
    """
    Parses and aggregates discovered files into concrete ForecastCycle objects.
    Enforces scientific rule:
      Only expose cycles actually present. Never fabricate cycles.
    """

    @classmethod
    def parse_cycle_info(cls, filename: str) -> Optional[Tuple[str, str, int, Optional[int]]]:
        """
        Extracts (date_str, cycle_str, cycle_hour, lead_time) from typical meteorological naming:
          ncum_20260715_00z_f024.nc -> ('2026-07-15', '00 UTC', 0, 24)
          gfs_20260715_12z_f048.nc -> ('2026-07-15', '12 UTC', 12, 48)
        """
        # Pattern 1: {model}_{YYYYMMDD}_{HH}z_f{lead}.nc
        m = re.search(r"(\d{8})_(\d{2})z(?:_f(\d{2,3}))?", filename, re.IGNORECASE)
        if m:
            date_raw = m.group(1)
            hour_raw = int(m.group(2))
            lead_raw = int(m.group(3)) if m.group(3) else None
            try:
                date_fmt = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
                cycle_utc = CYCLE_HOURS.get(hour_raw, f"{hour_raw:02d} UTC")
                return date_fmt, cycle_utc, hour_raw, lead_raw
            except Exception:
                pass

        # Pattern 2: {YYYY-MM-DD}_{HH}UTC
        m2 = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})UTC", filename, re.IGNORECASE)
        if m2:
            date_fmt = m2.group(1)
            hour_raw = int(m2.group(2))
            cycle_utc = CYCLE_HOURS.get(hour_raw, f"{hour_raw:02d} UTC")
            lead = LeadTimeNormalizer.extract_lead_from_filename(filename)
            return date_fmt, cycle_utc, hour_raw, lead

        return None

    @classmethod
    def aggregate_cycles_from_files(
        cls,
        files: List[Path],
        model_name: str,
        provider_id: str,
        data_mode: str,
        checksums: Optional[Dict[str, str]] = None,
    ) -> List[ForecastCycle]:
        """
        Groups actual discovered files into forecast cycles without inventing missing leads.
        """
        cycles_map: Dict[str, Dict[str, Any]] = {}
        checksums = checksums or {}

        for f in files:
            parsed = cls.parse_cycle_info(f.name)
            if not parsed:
                continue
            date_fmt, cycle_utc, cycle_hour, lead = parsed
            cycle_id = f"{model_name}_{date_fmt.replace('-', '')}_{cycle_hour:02d}Z"

            if cycle_id not in cycles_map:
                dt_iso = f"{date_fmt}T{cycle_hour:02d}:00:00Z"
                cycles_map[cycle_id] = {
                    "cycle_id": cycle_id,
                    "date": date_fmt,
                    "cycle_utc": cycle_utc,
                    "cycle_hour": cycle_hour,
                    "model": model_name,
                    "provider_id": provider_id,
                    "initialization_time": dt_iso,
                    "available_leads": set(),
                    "files": [],
                    "file_hashes": {},
                    "data_mode": data_mode,
                }

            cycles_map[cycle_id]["files"].append(f.name)
            if lead is not None:
                cycles_map[cycle_id]["available_leads"].add(lead)
            if f.name in checksums:
                cycles_map[cycle_id]["file_hashes"][f.name] = checksums[f.name]

        result: List[ForecastCycle] = []
        for c in cycles_map.values():
            leads = sorted(list(c["available_leads"]))
            # Status determination
            if len(leads) >= 5:
                status = "COMPLETE"
            elif len(leads) > 0:
                status = "PARTIAL"
            elif len(c["files"]) > 0:
                status = "AVAILABLE"
            else:
                status = "EMPTY"

            result.append(
                ForecastCycle(
                    cycle_id=c["cycle_id"],
                    date=c["date"],
                    cycle_utc=c["cycle_utc"],
                    cycle_hour=c["cycle_hour"],
                    model=c["model"],
                    provider_id=c["provider_id"],
                    initialization_time=c["initialization_time"],
                    available_leads=leads,
                    status=status,
                    files=sorted(c["files"]),
                    file_hashes=c["file_hashes"],
                    data_mode=c["data_mode"],
                )
            )

        return sorted(result, key=lambda x: (x.date, x.cycle_hour), reverse=True)
