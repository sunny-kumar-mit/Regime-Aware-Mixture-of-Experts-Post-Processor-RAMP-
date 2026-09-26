"""
RAMP Scientific Verification, Explainability & Operational Jury Demonstration
SIH26080 | Phase 10 | MoES / NCMRWF

Scientific analysis layer built on top of Phases 1–9 verified outputs.
Provides transparent, reproducible, scientifically honest analysis.

IMPORTANT: SYNTHETIC_DEMO mode active.
Real IMD/NCMRWF observational archives are NOT mounted.
"""

from ml.scientific.verification import ScientificVerificationEngine
from ml.scientific.benchmarks import ModelBenchmarkComparison
from ml.scientific.thresholds import ThresholdVerificationEngine
from ml.scientific.regimes import RegimeStratifiedVerification
from ml.scientific.lead_time import LeadTimeVerification
from ml.scientific.spatial import SpatialVerificationEngine
from ml.scientific.calibration import CalibrationAnalyzer
from ml.scientific.significance import BootstrapSignificanceEngine
from ml.scientific.case_study import CaseStudyReplayEngine
from ml.scientific.explainability import ExplainabilityEngine
from ml.scientific.feature_attribution import FeatureAttributionEngine
from ml.scientific.expert_analysis import ExpertGatingAnalyzer
from ml.scientific.failure_analysis import FailureAnalysisEngine
from ml.scientific.registry import ScientificRegistry, SCIENTIFIC_VERSION
from ml.scientific.validation import ScientificValidator

__all__ = [
    "ScientificVerificationEngine",
    "ModelBenchmarkComparison",
    "ThresholdVerificationEngine",
    "RegimeStratifiedVerification",
    "LeadTimeVerification",
    "SpatialVerificationEngine",
    "CalibrationAnalyzer",
    "BootstrapSignificanceEngine",
    "CaseStudyReplayEngine",
    "ExplainabilityEngine",
    "FeatureAttributionEngine",
    "ExpertGatingAnalyzer",
    "FailureAnalysisEngine",
    "ScientificRegistry",
    "SCIENTIFIC_VERSION",
    "ScientificValidator",
]
