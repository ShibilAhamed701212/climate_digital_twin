"""DataSourceManager — central authority for all climate data access.

Every consumer (dashboard, copilot, forecast, risk, scenario, twin)
must call DataSourceManager. Consumers must NEVER implement provider
logic or data generation themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.providers.base import BaseProvider
    from pipeline.providers.historical_store import HistoricalStore
    from pipeline.providers.cache import ObservationCache


class ObservationStatus(Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    HISTORICAL = "HISTORICAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class Observation:
    """A single climate observation with full provenance metadata."""

    status: ObservationStatus = ObservationStatus.UNAVAILABLE
    provider: str = ""
    observation_timestamp: str = ""
    retrieved_timestamp: str = ""
    age_seconds: float = 0.0
    confidence: float = 0.0
    data_source_identifier: str = ""
    dataset_version: str = ""
    values: dict[str, float] = field(default_factory=dict)
    location_id: str = ""
    variable: str = ""
    message: str = ""

    @classmethod
    def unavailable(cls, location_id: str, variable: str, message: str = "") -> Observation:
        return cls(
            status=ObservationStatus.UNAVAILABLE,
            location_id=location_id,
            variable=variable,
            message=message or "No verified climate observations available.",
            retrieved_timestamp=datetime.now(timezone.utc).isoformat(),
        )


class DataSourceManager:
    """Central authority for climate data access with cascading fallback.

    Resolution order:
    1. LIVE — try providers in priority order
    2. CACHED — check observation cache
    3. HISTORICAL — check bundled archive datasets
    4. UNAVAILABLE — no data exists
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._providers: list[BaseProvider] = []
        self._historical_store: HistoricalStore | None = None
        self._cache: ObservationCache | None = None

    def get_observation(self, location_id: str, variable: str, timestamp: str | None = None) -> Observation:
        """Get the best available observation for a location/variable.

        Returns the highest-priority observation available, following
        the LIVE -> CACHED -> HISTORICAL -> UNAVAILABLE cascade.
        """
        # 1. Try LIVE providers
        for provider in self._providers:
            if not provider.is_available():
                continue
            try:
                obs = provider.fetch(location_id, variable, timestamp)
                if obs is not None:
                    self._save_to_cache(obs)
                    return obs
            except Exception:
                continue

        # 2. Try cache
        cached = self._get_from_cache(location_id, variable, timestamp)
        if cached is not None:
            return cached

        # 3. Try historical store
        if self._historical_store is not None:
            historical = self._historical_store.lookup(location_id, variable, timestamp)
            if historical is not None:
                return historical

        # 4. Unavailable
        return Observation.unavailable(location_id, variable)

    def _save_to_cache(self, obs: Observation) -> None:
        if self._cache is not None:
            self._cache.save(obs)

    def _get_from_cache(self, location_id: str, variable: str, timestamp: str | None) -> Observation | None:
        if self._cache is None:
            return None
        return self._cache.get(location_id, variable, timestamp)
