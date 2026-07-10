"""Conflict detection and resolution for Digital Twin states.

When multiple data sources provide different values for the same entity,
the conflict resolver detects discrepancies and resolves them according
to configurable strategies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from simulator.models.twin_state import TwinState

_logger = logging.getLogger(__name__)

SOURCE_PRIORITY: dict[str, int] = {
    "imd": 100,
    "era5": 80,
    "weather_station": 70,
    "noaa": 60,
    "open_meteo": 40,
    "synthetic": 10,
}


class ResolutionStrategy(StrEnum):
    """Strategy for resolving state conflicts between multiple sources."""

    SOURCE_PRIORITY = "source_priority"
    """Trust sources in priority order (IMD > ERA5 > Open-Meteo)."""

    HIGHEST_CONFIDENCE = "highest_confidence"
    """Use the value with highest confidence based on quality flags."""

    MOST_RECENT = "most_recent"
    """Use the most recent observation."""

    WEIGHTED_AVERAGE = "weighted_average"
    """Weight values by source confidence and compute an average."""

    MANUAL = "manual"
    """Flag for human review — no automatic resolution."""


@dataclass
class ConflictRecord:
    """A record of a detected conflict between twin states.

    Attributes:
        entity_id: The entity with conflicting states.
        states: The conflicting states from different sources.
        sources: The sources that provided the conflicting states.
        timestamp: When the conflict was detected.
        variables: The variable names where conflicts exist.
        resolved: Whether this conflict has been resolved.
        resolution_strategy: The strategy used to resolve (if resolved).
        resolved_by: Who/what resolved the conflict.
        resolved_at: When the conflict was resolved.
    """

    entity_id: str
    states: list[TwinState]
    sources: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    variables: list[str] = field(default_factory=list)
    resolved: bool = False
    resolution_strategy: ResolutionStrategy | None = None
    resolved_by: str = ""
    resolved_at: datetime | None = None
    conflict_id: str = ""

    def __post_init__(self) -> None:
        """Generate default conflict_id if not provided."""
        import uuid

        if not self.conflict_id:
            self.conflict_id = uuid.uuid4().hex[:16]


_CONFIDENCE_MAP: dict[str, int] = {
    "validated": 100,
    "corrected": 80,
    "raw": 50,
    "estimated": 30,
    "suspicious": 10,
    "missing": 0,
}


class ConflictResolver:
    """Resolves conflicts between twin states from different sources.

    Detects discrepancies between states from different data sources and
    applies the configured resolution strategy to produce a single
    reconciled state.
    """

    def __init__(
        self, default_strategy: ResolutionStrategy = ResolutionStrategy.SOURCE_PRIORITY
    ) -> None:
        """Initialize the conflict resolver.

        Args:
            default_strategy: The default strategy to use for resolution.
        """
        self._default_strategy = default_strategy

    def detect_conflicts(self, states: list[TwinState]) -> list[ConflictRecord]:
        """Detect conflicts between a list of twin states.

        Compares states from different sources for the same entity and
        identifies variables with differing values beyond a small tolerance.

        Args:
            states: List of twin states (typically from different sources).

        Returns:
            A list of ConflictRecord entries for each detected conflict.
        """
        if len(states) < 2:
            return []

        if not states:
            return []

        entity_id = states[0].entity_id
        if not all(s.entity_id == entity_id for s in states):
            raise ValueError("All states must belong to the same entity")

        # Group states by source
        source_map: dict[str, TwinState] = {}
        for s in states:
            source_map[s.data_source] = s

        sources = list(source_map.keys())
        if len(sources) < 2:
            return []

        # Check each variable for conflicts
        conflict_vars: list[str] = []
        numeric_vars = [
            "temperature_2m",
            "precipitation_mm",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_10m",
            "wind_direction_10m",
        ]
        optional_vars = [
            "solar_radiation",
            "cloud_cover_pct",
            "soil_moisture",
        ]

        for var in numeric_vars:
            values = [getattr(source_map[s], var) for s in sources if s in source_map]
            if len(values) >= 2 and max(values) - min(values) > 0.1:
                conflict_vars.append(var)

        for var in optional_vars:
            values = [
                getattr(source_map[s], var)
                for s in sources
                if s in source_map and getattr(source_map[s], var) is not None
            ]
            if len(values) >= 2 and max(values) - min(values) > 0.1 and var not in conflict_vars:
                conflict_vars.append(var)

        if not conflict_vars:
            return []

        return [
            ConflictRecord(
                entity_id=entity_id,
                states=list(source_map.values()),
                sources=sources,
                variables=conflict_vars,
            )
        ]

    def _get_quality_confidence(self, state: TwinState) -> int:
        """Get numeric confidence based on quality flag."""
        return _CONFIDENCE_MAP.get(state.quality_flag, 50)

    @staticmethod
    def _lookup_confidence(quality_flag: str) -> int:
        """Look up numeric confidence for a quality flag string."""
        return _CONFIDENCE_MAP.get(quality_flag, 50)

    def _get_source_priority(self, source: str) -> int:
        """Get numeric priority for a data source."""
        return SOURCE_PRIORITY.get(source.lower(), 0)

    def resolve(
        self,
        conflict: ConflictRecord,
        strategy: ResolutionStrategy | None = None,
    ) -> TwinState:
        """Resolve a conflict using the specified strategy.

        Args:
            conflict: The conflict record to resolve.
            strategy: Strategy to use. Falls back to default if None.

        Returns:
            A single TwinState representing the resolved state.

        Raises:
            ValueError: If the strategy requires more information or
                if resolution is not possible.
        """
        strategy = strategy or self._default_strategy

        if strategy == ResolutionStrategy.MANUAL:
            raise ValueError(f"Conflict {conflict.conflict_id} requires manual resolution")

        resolver = {
            ResolutionStrategy.SOURCE_PRIORITY: self._resolve_by_source_priority,
            ResolutionStrategy.HIGHEST_CONFIDENCE: self._resolve_by_highest_confidence,
            ResolutionStrategy.MOST_RECENT: self._resolve_by_most_recent,
            ResolutionStrategy.WEIGHTED_AVERAGE: self._resolve_by_weighted_average,
        }

        resolved_fn = resolver.get(strategy)
        if resolved_fn is None:
            raise ValueError(f"Unknown resolution strategy: {strategy}")

        resolved_state = resolved_fn(conflict)

        # Mark conflict as resolved
        conflict.resolved = True
        conflict.resolution_strategy = strategy
        conflict.resolved_at = datetime.now(UTC)
        conflict.resolved_by = "ConflictResolver"

        _logger.info(
            "Resolved conflict '%s' for entity '%s' using %s",
            conflict.conflict_id,
            conflict.entity_id,
            strategy.value,
        )

        return resolved_state

    def _resolve_by_source_priority(self, conflict: ConflictRecord) -> TwinState:
        """Resolve by picking the state from the highest-priority source."""
        best_source = max(conflict.sources, key=lambda s: self._get_source_priority(s))
        idx = conflict.sources.index(best_source)
        return conflict.states[idx]

    def _resolve_by_highest_confidence(self, conflict: ConflictRecord) -> TwinState:
        """Resolve by picking the state with the highest quality confidence."""
        best_idx = max(
            range(len(conflict.states)),
            key=lambda i: self._get_quality_confidence(conflict.states[i]),
        )
        return conflict.states[best_idx]

    def _resolve_by_most_recent(self, conflict: ConflictRecord) -> TwinState:
        """Resolve by picking the most recent state."""
        best_idx = max(
            range(len(conflict.states)),
            key=lambda i: conflict.states[i].timestamp,
        )
        return conflict.states[best_idx]

    def _resolve_by_weighted_average(self, conflict: ConflictRecord) -> TwinState:
        """Resolve by computing a weighted average across sources."""
        import copy

        weights: list[float] = []
        for s in conflict.states:
            source_weight = self._get_source_priority(s.data_source)
            confidence_weight = self._lookup_confidence(s.quality_flag)
            weights.append(float(source_weight + confidence_weight))

        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0] * len(weights)
            total_weight = sum(weights)

        normalized_weights = [w / total_weight for w in weights]

        # Use the most complete state as the base
        base_state = copy.deepcopy(conflict.states[0])

        numeric_vars = [
            "temperature_2m",
            "precipitation_mm",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_10m",
            "wind_direction_10m",
        ]
        optional_vars = [
            "solar_radiation",
            "cloud_cover_pct",
            "soil_moisture",
        ]

        for var in numeric_vars:
            weighted_val = 0.0
            for i, s in enumerate(conflict.states):
                weighted_val += getattr(s, var) * normalized_weights[i]
            setattr(base_state, var, weighted_val)

        for var in optional_vars:
            values_with_weights = [
                (getattr(s, var), normalized_weights[i])
                for i, s in enumerate(conflict.states)
                if getattr(s, var) is not None
            ]
            if values_with_weights:
                weighted_val = sum(v * w for v, w in values_with_weights)
                total_w = sum(w for _, w in values_with_weights)
                setattr(base_state, var, weighted_val / total_w if total_w > 0 else None)

        return base_state

    def resolve_all(
        self,
        conflicts: list[ConflictRecord],
        strategy: ResolutionStrategy | None = None,
    ) -> list[TwinState]:
        """Resolve multiple conflicts using the specified strategy.

        Args:
            conflicts: List of conflict records to resolve.
            strategy: Strategy to use for all conflicts.

        Returns:
            List of resolved TwinState objects.
        """
        return [self.resolve(c, strategy) for c in conflicts]


__all__ = [
    "ConflictResolver",
    "ConflictRecord",
    "ResolutionStrategy",
    "SOURCE_PRIORITY",
]
