"""
RAMP Provider Registry
SIH26080 | Central Registry for All Data Providers

Provides a single registry where providers are registered at startup.
Allows the API to enumerate providers, check status, and route requests.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ramp.ingestion.base import (
    ObservationProvider,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    WeatherForecastProvider,
)

logger = logging.getLogger("ramp.ingestion.registry")


class ProviderRegistry:
    """Central registry for all RAMP data providers."""

    def __init__(self) -> None:
        self._nwp: Dict[str, WeatherForecastProvider] = {}
        self._obs: Dict[str, ObservationProvider] = {}

    def register_nwp(self, provider: WeatherForecastProvider) -> None:
        self._nwp[provider.provider_id] = provider
        logger.info("Registered NWP provider: %s", provider.provider_id)

    def register_obs(self, provider: ObservationProvider) -> None:
        self._obs[provider.provider_id] = provider
        logger.info("Registered observation provider: %s", provider.provider_id)

    def get_nwp(self, provider_id: str) -> Optional[WeatherForecastProvider]:
        return self._nwp.get(provider_id)

    def get_obs(self, provider_id: str) -> Optional[ObservationProvider]:
        return self._obs.get(provider_id)

    def list_all_providers(self) -> List[ProviderInfo]:
        infos = []
        for p in self._nwp.values():
            infos.append(p.get_info())
        for p in self._obs.values():
            infos.append(p.get_info())
        return infos

    def list_nwp_providers(self) -> List[ProviderInfo]:
        return [p.get_info() for p in self._nwp.values()]

    def list_obs_providers(self) -> List[ProviderInfo]:
        return [p.get_info() for p in self._obs.values()]

    @property
    def provider_count(self) -> int:
        return len(self._nwp) + len(self._obs)


def build_default_registry() -> ProviderRegistry:
    """Build the default RAMP provider registry with all known providers."""
    from ramp.ingestion.gfs_adapter import GFSProvider
    from ramp.ingestion.gefs_adapter import GEFSProvider
    from ramp.ingestion.ncmrwf_adapter import NCMRWFProvider
    from ramp.ingestion.imd_adapter import IMDObservationProvider
    from ramp.ingestion.synthetic_generator import (
        SyntheticNWPProvider,
        SyntheticObservationProvider,
    )

    registry = ProviderRegistry()

    # NWP providers
    registry.register_nwp(GFSProvider())
    registry.register_nwp(GEFSProvider())
    registry.register_nwp(NCMRWFProvider(model_name="NCUM"))
    registry.register_nwp(NCMRWFProvider(model_name="NEPS", is_ensemble=True))
    registry.register_nwp(SyntheticNWPProvider())

    # Observation providers
    registry.register_obs(IMDObservationProvider())
    registry.register_obs(SyntheticObservationProvider())

    logger.info(
        "Provider registry built: %d NWP, %d obs providers",
        len(registry.list_nwp_providers()),
        len(registry.list_obs_providers()),
    )
    return registry


# Module-level singleton — initialized on first import
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = build_default_registry()
    return _registry
