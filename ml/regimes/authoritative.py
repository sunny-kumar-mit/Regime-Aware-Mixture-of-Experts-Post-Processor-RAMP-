"""
RAMP Authoritative Regime Label Provider Architecture
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Interface and registry for authoritative ground-truth regime datasets
(e.g. IMD Monsoon Bulletins, NCMRWF Synoptic Catalogues, Cyclone e-Atlas).

Honesty Rule:
  If no authoritative labels are loaded, explicitly report UNAVAILABLE.
  Never fabricate authoritative ground-truth labels.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from ml.regimes.definitions import LabelQuality, LabelSource, WeatherRegime


class AuthoritativeRegimeLabelProvider(ABC):
    """Abstract interface for external authoritative regime catalogue ingestion."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the authoritative institution or catalogue."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether authoritative records are currently present in local storage."""
        pass

    @abstractmethod
    def get_labels_for_period(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Retrieves authoritative regime labels for a given time window.
        Returns DataFrame with columns: [valid_time, latitude, longitude, regime_label, regime_label_source, regime_label_confidence]
        """
        pass


class IMDMonsoonBulletinProvider(AuthoritativeRegimeLabelProvider):
    """
    Adapter for IMD Official Monsoon Daily Weather Reports and Depression Bulletins.
    """

    def __init__(self, catalogue_path: Optional[str] = None):
        self.catalogue_path = catalogue_path

    @property
    def provider_name(self) -> str:
        return "IMD_MONSOON_BULLETINS"

    @property
    def is_available(self) -> bool:
        # Currently not loaded in local environment
        return False

    def get_labels_for_period(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        if not self.is_available:
            raise FileNotFoundError(
                "Authoritative IMD regime catalogue is NOT AVAILABLE in local storage. "
                "Weak rules (WEAK_RULE) or SYNTHETIC_DEMO labels must be used."
            )
        return pd.DataFrame()


class AuthoritativeLabelRegistry:
    """Manages registered authoritative regime providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, AuthoritativeRegimeLabelProvider] = {
            "imd_bulletins": IMDMonsoonBulletinProvider()
        }

    def list_providers(self) -> List[Dict[str, Any]]:
        return [
            {"provider_id": pid, "name": p.provider_name, "available": p.is_available}
            for pid, p in self._providers.items()
        ]

    def has_any_available(self) -> bool:
        return any(p.is_available for p in self._providers.values())


authoritative_registry = AuthoritativeLabelRegistry()
