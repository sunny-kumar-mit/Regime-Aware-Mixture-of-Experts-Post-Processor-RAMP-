"""
Phase 8 Operational Readiness Level Evaluation
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Defines the 6 engineering readiness tiers:
  LEVEL 0: Synthetic Demonstration (Active default)
  LEVEL 1: Real Data Ingested
  LEVEL 2: Real Data Quality Validated
  LEVEL 3: Historical Real-Data Verification Complete
  LEVEL 4: Extended Multi-Season Verification
  LEVEL 5: Operational Deployment Candidate

IMPORTANT:
These are engineering readiness states.
Do NOT call Level 5 "official operational approval."
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from ml.data.providers.real_provider import RealDataProvider
from ml.data.manifest import DatasetManifest


@dataclass
class ReadinessTier:
    level: int
    name: str
    description: str
    status: str  # ACHIEVED, CURRENT_ACTIVE, IN_PROGRESS, NOT_STARTED
    criteria_met: List[str]
    pending_criteria: List[str]


@dataclass
class OperationalReadinessAssessment:
    current_level: int
    current_level_name: str
    data_mode: str
    is_real_data_available: bool
    summary: str
    disclaimer: str
    tiers: List[ReadinessTier]


class OperationalReadinessEvaluator:
    """Evaluates the project against the 6 engineering readiness levels."""

    def evaluate(self) -> OperationalReadinessAssessment:
        provider = RealDataProvider()
        manifest = DatasetManifest.load()
        has_real = provider.is_real_data_available()

        # By default, since real archives are not mounted in the repo, level is LEVEL 0
        current_level = 0
        current_name = "LEVEL 0: Synthetic Demonstration"

        tiers = [
            ReadinessTier(
                level=0,
                name="Synthetic Demonstration",
                description="Pipeline validated end-to-end on synthetic meteorological demonstration datasets.",
                status="ACHIEVED",
                criteria_met=[
                    "Phase 1 Production foundation verified",
                    "Phase 2 Data ingestion architecture implemented",
                    "Phase 3 Feature engineering & LeakageGuard operational",
                    "Phase 4 Weather Regime Intelligence Engine trained & frozen",
                    "Phase 5 Baseline post-processing suite benchmarked & frozen",
                    "Phase 6 RAMP Mixture-of-Experts verified & frozen",
                    "Phase 7 Extreme Rainfall Probability Engine operational",
                    "Phase 8 Real-data adapters and contracts in place",
                ],
                pending_criteria=[],
            ),
            ReadinessTier(
                level=1,
                name="Real Data Ingested",
                description="Physical NetCDF/GRIB archives from IMD/NCMRWF mounted and parsed into canonical schema.",
                status="ACHIEVED" if has_real else "IN_PROGRESS",
                criteria_met=["Real data provider adapters built (NetCDF, GRIB, Parquet, CSV)"] + (["Physical real data mounted"] if has_real else []),
                pending_criteria=[] if has_real else ["Mount authoritative IMD 0.25° gridded rainfall archives", "Mount NCMRWF NCUM forecast cycles"],
            ),
            ReadinessTier(
                level=2,
                name="Real Data Quality Validated",
                description="13-point meteorological quality control and physical sanity checks executed with PASS status.",
                status="NOT_STARTED" if not has_real else "IN_PROGRESS",
                criteria_met=["MeteorologicalQualityControl engine implemented with 13 checks"],
                pending_criteria=["Execute QC on real operational data archive", "Achieve PASS status on real dataset manifest"],
            ),
            ReadinessTier(
                level=3,
                name="Historical Real-Data Verification Complete",
                description="Full verification matrix (continuous, threshold, probability, bootstrap) computed on historical real data.",
                status="NOT_STARTED",
                criteria_met=["Unified verification engine consuming all 6 systems implemented"],
                pending_criteria=["Compute real-data benchmark on >= 1 complete monsoon season (JJAS)"],
            ),
            ReadinessTier(
                level=4,
                name="Extended Multi-Season Verification",
                description="Cross-season validation across at least 3 distinct historical Indian Summer Monsoon seasons.",
                status="NOT_STARTED",
                criteria_met=[],
                pending_criteria=["Verify inter-annual stability across contrasting drought and excess monsoon years"],
            ),
            ReadinessTier(
                level=5,
                name="Operational Deployment Candidate",
                description="Candidate ready for operational parallel runs alongside NCMRWF operational forecast suites.",
                status="NOT_STARTED",
                criteria_met=["Automated pipeline replay and CLI tooling in place"],
                pending_criteria=[
                    "Live daily forecast ingestion testing",
                    "NCMRWF high-performance computing environment verification",
                    "Operational forecaster feedback review",
                ],
            ),
        ]

        if has_real:
            current_level = 1
            current_name = "LEVEL 1: Real Data Ingested"

        disclaimer = (
            "NOTICE: Operational Readiness Levels represent internal engineering maturation milestones. "
            "Level 5 denotes an 'Operational Deployment Candidate' from a software engineering perspective "
            "and does NOT represent official MoES/NCMRWF operational certification."
        )

        return OperationalReadinessAssessment(
            current_level=current_level,
            current_level_name=current_name,
            data_mode="REAL" if has_real else "SYNTHETIC_DEMO",
            is_real_data_available=has_real,
            summary=(
                f"Currently operating at {current_name}. All core Phase 1-8 engines, models, "
                "APIs, and dashboards are complete and active in honest SYNTHETIC_DEMO mode."
            ),
            disclaimer=disclaimer,
            tiers=tiers,
        )
