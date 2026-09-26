"""
RAMP Weather Regime Definitions & Taxonomy
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Canonical 7 weather regimes and taxonomy specifications.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class WeatherRegime(str, Enum):
    """The 7 canonical meteorological weather regimes for the Indian monsoon."""
    ACTIVE_MONSOON = "ACTIVE_MONSOON"
    BREAK_MONSOON = "BREAK_MONSOON"
    LOW_DEPRESSION = "LOW_DEPRESSION"
    COASTAL = "COASTAL"
    OROGRAPHIC = "OROGRAPHIC"
    WESTERN_DISTURBANCE = "WESTERN_DISTURBANCE"
    TRANSITION_OTHER = "TRANSITION_OTHER"


REGIME_ORDER: List[WeatherRegime] = [
    WeatherRegime.ACTIVE_MONSOON,
    WeatherRegime.BREAK_MONSOON,
    WeatherRegime.LOW_DEPRESSION,
    WeatherRegime.COASTAL,
    WeatherRegime.OROGRAPHIC,
    WeatherRegime.WESTERN_DISTURBANCE,
    WeatherRegime.TRANSITION_OTHER,
]

REGIME_TO_INT: Dict[str, int] = {regime.value: idx for idx, regime in enumerate(REGIME_ORDER)}
INT_TO_REGIME: Dict[int, str] = {idx: regime.value for idx, regime in enumerate(REGIME_ORDER)}


class LabelSource(str, Enum):
    """Provenance of assigned regime label."""
    WEAK_RULE = "WEAK_RULE"
    AUTHORITATIVE = "AUTHORITATIVE"
    CLUSTERING = "CLUSTERING"
    SYNTHETIC = "SYNTHETIC"


class LabelQuality(str, Enum):
    """Quality tier of assigned regime label."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNAVAILABLE = "UNAVAILABLE"


class UncertaintyLevel(str, Enum):
    """Categorical uncertainty level derived from Shannon entropy."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TransitionState(str, Enum):
    """Temporal dynamics state between sequential forecasts."""
    STABLE = "STABLE"
    TRANSITIONING = "TRANSITIONING"
    HIGH_VARIANCE = "HIGH_VARIANCE"


class RegimeDefinition(BaseModel):
    """Metadata specification for a single weather regime."""
    id: str
    code: int
    name: str
    description: str
    seasonal_applicability: List[str] = Field(default_factory=list)
    months: List[int] = Field(default_factory=list)
    spatial_domain: str = ""
    indicators: Dict[str, Any] = Field(default_factory=dict)
    confidence_rules: Dict[str, float] = Field(default_factory=dict)
    source_reference: str = ""
    limitations: str = ""


class RegimeDefinitionRegistry:
    """Manages regime definitions loaded from config/regimes.yaml."""

    def __init__(self, config_path: Optional[Path] = None):
        self._definitions: Dict[str, RegimeDefinition] = {}
        self.config_path = config_path or Path("config/regimes.yaml")
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            regimes_data = data.get("regimes", {})
            for r_id, r_info in regimes_data.items():
                self._definitions[r_id] = RegimeDefinition(**r_info)
        else:
            # Fallback to standard programmatic defaults
            for idx, r_enum in enumerate(REGIME_ORDER):
                self._definitions[r_enum.value] = RegimeDefinition(
                    id=r_enum.value,
                    code=idx,
                    name=r_enum.value.replace("_", " ").title(),
                    description=f"Meteorological regime {r_enum.value}",
                    source_reference="RAMP Monsoon Specification",
                )

    def get(self, regime: WeatherRegime | str) -> Optional[RegimeDefinition]:
        key = regime.value if isinstance(regime, WeatherRegime) else regime
        return self._definitions.get(key)

    def list_regimes(self) -> List[RegimeDefinition]:
        return [self._definitions[r.value] for r in REGIME_ORDER if r.value in self._definitions]


# Global singleton registry
regime_registry = RegimeDefinitionRegistry()
