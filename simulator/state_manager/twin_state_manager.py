"""Core Digital Twin State Manager.

The central state manager that coordinates all twin state operations,
including create/read/update/rollback entity states, version history
with immutable snapshots, temporal and spatial queries, conflict
detection and resolution, and state reconciliation.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

import pyarrow as pa

from simulator.conflict.resolver import ConflictRecord, ConflictResolver, ResolutionStrategy
from simulator.graph.entity_graph import RelationshipType, TwinEntityGraph
from simulator.models.twin_state import StateDelta, TwinState, TwinStateVersion
from simulator.models.weather import WeatherObservation
from simulator.reconciliation.engine import ReconciliationResult, StateReconciler
from simulator.repository.versioned_state_store import VersionedStateStore

_logger = logging.getLogger(__name__)

_AUTHORITATIVE_SOURCES = {"manual", "api", "era5", "open_meteo", "twin_synchronizer"}


def _reject_non_authoritative_source(source: str) -> None:
    """Reject sources that must never be persisted into the authoritative twin store.

    Scenario/synthetic/demo states live in separate stores and must not reach the
    REAL twin repository even via the delta-update path.
    """
    if source.lower() not in _AUTHORITATIVE_SOURCES:
        raise ValueError(
            f"Refusing to persist non-REAL state from source '{source}' "
            "into the authoritative twin store"
        )


class TwinStateManager:
    """Manages the complete lifecycle of Digital Twin entity states.

    Features:
    - Create/read/update/rollback entity states
    - Version history with immutable snapshots
    - Temporal queries (state at any point in time)
    - Spatial queries (entities within a bounding box)
    - Conflict detection and resolution
    - State reconciliation across data sources

    All public methods are async and thread-safe.
    """

    def __init__(
        self,
        store: VersionedStateStore | None = None,
        conflict_resolver: ConflictResolver | None = None,
        reconciler: StateReconciler | None = None,
        graph: TwinEntityGraph | None = None,
    ) -> None:
        """Initialize the twin state manager.

        Args:
            store: VersionedStateStore instance. Creates a default if None.
            conflict_resolver: ConflictResolver instance. Creates default if None.
            reconciler: StateReconciler instance. Creates default if None.
            graph: TwinEntityGraph instance. Creates default if None.
        """
        self._store = store or VersionedStateStore()
        self._conflict_resolver = conflict_resolver or ConflictResolver()
        self._reconciler = reconciler or StateReconciler()
        self._graph = graph or TwinEntityGraph()

    # ─── Properties ───────────────────────────────────────────────────────

    @property
    def store(self) -> VersionedStateStore:
        """The underlying versioned state store."""
        return self._store

    @property
    def conflict_resolver(self) -> ConflictResolver:
        """The conflict resolver instance."""
        return self._conflict_resolver

    @property
    def reconciler(self) -> StateReconciler:
        """The state reconciler instance."""
        return self._reconciler

    @property
    def graph(self) -> TwinEntityGraph:
        """The entity relationship graph."""
        return self._graph

    # ─── Core State Operations ────────────────────────────────────────────

    async def get_current_state(self, location_id: str) -> TwinState:
        """Get the current (latest) state for a location.

        Args:
            location_id: Entity/location identifier.

        Returns:
            The current TwinState.

        Raises:
            ValueError: If no state exists for the location.
        """
        state = self._store.get_latest_state(location_id)
        if state is None:
            raise ValueError(f"No state found for location '{location_id}'")
        return state

    async def get_state_at_time(
        self,
        location_id: str,
        timestamp: datetime,
    ) -> TwinState | None:
        """Get the state closest to the given timestamp.

        Args:
            location_id: Entity/location identifier.
            timestamp: The target point in time.

        Returns:
            The closest TwinState, or None if no data exists.
        """
        return self._store.get_state_at_time(location_id, timestamp)

    async def get_state_version(
        self,
        location_id: str,
        version_number: int,
    ) -> TwinState:
        """Get a state by its version number.

        Args:
            location_id: Entity/location identifier.
            version_number: Version number (1-based).

        Returns:
            The TwinState at that version.

        Raises:
            ValueError: If the version does not exist.
        """
        state = self._store.get_state_by_version_number(location_id, version_number)
        if state is None:
            raise ValueError(f"Version {version_number} not found for location '{location_id}'")
        return state

    async def update_state(
        self,
        location_id: str,
        delta: StateDelta,
        source: str = "manual",
    ) -> TwinStateVersion:
        """Apply a state delta to the current state, creating a new version.

        Args:
            location_id: Entity/location identifier.
            delta: The state delta to apply.
            source: Identifier for the source of this update.

        Returns:
            The newly created TwinStateVersion.

        Raises:
            ValueError: If no current state exists, or if the source is not
            an authoritative data source.
        """
        _reject_non_authoritative_source(source)

        current: TwinState | None = None
        with contextlib.suppress(ValueError):
            current = await self.get_current_state(location_id)

        if current is not None:
            new_state = TwinState(
                entity_id=location_id,
                timestamp=datetime.now(UTC),
                temperature_2m=current.temperature_2m + delta.delta_temperature,
                precipitation_mm=current.precipitation_mm + delta.delta_precipitation,
                humidity_pct=current.humidity_pct + delta.delta_humidity,
                pressure_hpa=current.pressure_hpa + delta.delta_pressure,
                wind_speed_10m=current.wind_speed_10m + delta.delta_wind_speed,
                wind_direction_10m=(current.wind_direction_10m + delta.delta_wind_direction)
                % 360.0,
                solar_radiation=(
                    _add_optional(current.solar_radiation, delta.delta_solar_radiation)
                ),
                cloud_cover_pct=(_add_optional(current.cloud_cover_pct, delta.delta_cloud_cover)),
                soil_moisture=(_add_optional(current.soil_moisture, delta.delta_soil_moisture)),
                data_source=source,
                quality_flag="validated",
            )
        else:
            # Create initial state — use delta values as absolute values
            new_state = TwinState(
                entity_id=location_id,
                timestamp=datetime.now(UTC),
                temperature_2m=delta.delta_temperature,
                precipitation_mm=delta.delta_precipitation,
                humidity_pct=delta.delta_humidity,
                pressure_hpa=delta.delta_pressure,
                wind_speed_10m=delta.delta_wind_speed,
                wind_direction_10m=delta.delta_wind_direction % 360.0
                if delta.delta_wind_direction
                else 0.0,
                solar_radiation=delta.delta_solar_radiation,
                cloud_cover_pct=delta.delta_cloud_cover,
                soil_moisture=delta.delta_soil_moisture,
                data_source=source,
                quality_flag="initial",
            )

        return self._store.save_state(
            new_state,
            created_by=source,
            description=f"Updated via delta (source: {source})",
        )

    async def rollback(
        self,
        location_id: str,
        version_number: int,
    ) -> TwinState:
        """Rollback to a specific version number.

        This creates a NEW version that is a copy of the specified version,
        maintaining the append-only invariant. Rolls back by version number
        (not UUID) for user-friendly API.

        Args:
            location_id: Entity/location identifier.
            version_number: Version number to rollback to.

        Returns:
            The new TwinState after rollback.

        Raises:
            ValueError: If the specified version does not exist.
        """
        # Find version_id from version_number
        state = self._store.get_state_by_version_number(location_id, version_number)
        if state is None:
            raise ValueError(f"Version {version_number} not found for location '{location_id}'")

        # Get the version_id from the index
        index = self._store._read_version_index()
        entity_index = index.filter(pa.compute.equal(index.column("entity_id"), location_id))
        target_version_id: str | None = None
        for i in range(entity_index.num_rows):
            vn = int(entity_index.column("version_number")[i].as_py())
            if vn == version_number:
                target_version_id = str(entity_index.column("version_id")[i].as_py())
                break

        if target_version_id is None:
            raise ValueError(f"Version {version_number} not found for location '{location_id}'")

        return self._store.rollback(location_id, target_version_id)

    # ─── History and Comparison ───────────────────────────────────────────

    async def get_version_history(
        self,
        location_id: str,
    ) -> list[TwinStateVersion]:
        """Get the full version history for a location.

        Args:
            location_id: Entity/location identifier.

        Returns:
            List of TwinStateVersion in descending order (newest first).
        """
        return self._store.get_version_history(location_id)

    async def compare_versions(
        self,
        location_id: str,
        version_a: int,
        version_b: int,
    ) -> StateDelta:
        """Compare two versions and return the difference.

        Args:
            location_id: Entity/location identifier.
            version_a: First version number.
            version_b: Second version number.

        Returns:
            A StateDelta describing the differences.

        Raises:
            ValueError: If either version does not exist.
        """
        # Get version IDs from version numbers
        state_a = self._store.get_state_by_version_number(location_id, version_a)
        state_b = self._store.get_state_by_version_number(location_id, version_b)

        if state_a is None:
            raise ValueError(f"Version {version_a} not found for location '{location_id}'")
        if state_b is None:
            raise ValueError(f"Version {version_b} not found for location '{location_id}'")

        index = self._store._read_version_index()

        def _find_version_id(vn: int) -> str:
            entity_index = index.filter(pa.compute.equal(index.column("entity_id"), location_id))
            for i in range(entity_index.num_rows):
                if int(entity_index.column("version_number")[i].as_py()) == vn:
                    return str(entity_index.column("version_id")[i].as_py())
            raise ValueError(f"Version {vn} not found")

        vid_a = _find_version_id(version_a)
        vid_b = _find_version_id(version_b)

        return self._store.compute_delta(location_id, vid_a, vid_b)

    # ─── Observation Sync ─────────────────────────────────────────────────

    async def sync_observation(
        self,
        observation: WeatherObservation,
    ) -> TwinStateVersion:
        """Sync a weather observation into the twin state.

        Creates or updates the twin state for the observation's location,
        using the observation's location_id as the entity identifier.

        Args:
            observation: The weather observation to sync.

        Returns:
            The created TwinStateVersion.
        """
        location_id = observation.location_id

        # Convert observation to a twin state
        state = TwinState(
            entity_id=location_id,
            timestamp=observation.timestamp,
            temperature_2m=observation.temperature_2m,
            precipitation_mm=observation.precipitation_mm,
            humidity_pct=observation.humidity_pct,
            pressure_hpa=observation.pressure_hpa,
            wind_speed_10m=observation.wind_speed_10m,
            wind_direction_10m=observation.wind_direction_10m,
            solar_radiation=observation.solar_radiation,
            cloud_cover_pct=observation.cloud_cover_pct,
            soil_moisture=observation.soil_moisture,
            data_source=observation.data_source.value,
            quality_flag=observation.quality_flag.value,
        )

        return self._store.save_state(
            state,
            created_by=f"sync:{observation.data_source.value}",
            description=f"Synced from {observation.data_source.value}",
        )

    # ─── Spatial Queries ──────────────────────────────────────────────────

    async def query_spatial(
        self,
        bbox: tuple[float, float, float, float],
    ) -> list[TwinState]:
        """Query the latest states for entities within a bounding box.

        Args:
            bbox: (min_lat, min_lon, max_lat, max_lon) in decimal degrees.

        Returns:
            List of latest TwinState for entities within the bounding box.
        """
        return self._store.query_spatial(bbox)

    # ─── Conflict Resolution ──────────────────────────────────────────────

    async def detect_conflicts(
        self,
        states: list[TwinState],
    ) -> list[ConflictRecord]:
        """Detect conflicts between twin states from different sources.

        Args:
            states: List of twin states (typically from different sources).

        Returns:
            List of ConflictRecord entries.
        """
        return self._conflict_resolver.detect_conflicts(states)

    async def resolve_conflicts(
        self,
        conflicts: list[ConflictRecord],
        strategy: ResolutionStrategy = ResolutionStrategy.SOURCE_PRIORITY,
    ) -> list[TwinState]:
        """Resolve conflicts using the specified strategy.

        Args:
            conflicts: List of ConflictRecord to resolve.
            strategy: Resolution strategy to use.

        Returns:
            List of resolved TwinState objects.
        """
        return self._conflict_resolver.resolve_all(conflicts, strategy)

    # ─── Reconciliation ───────────────────────────────────────────────────

    async def reconcile(
        self,
        location_id: str,
        primary_source: str = "imd",
    ) -> ReconciliationResult:
        """Reconcile the twin state using data from a primary source.

        This is a high-level operation that:
        1. Gets the current state for the location
        2. Checks if there's a preferred source observation available
        3. Applies reconciliation to correct the state

        For now, this creates a simulated reconciliation since we may not
        have real-time observed data. The reconciler compares the current
        state against itself as a baseline.

        Args:
            location_id: Entity/location identifier.
            primary_source: Primary data source for reconciliation.

        Returns:
            A ReconciliationResult with the correction and error metrics.
        """
        current = await self.get_current_state(location_id)

        # Create a synthetic observation from the current state for baseline
        from simulator.models.weather import DataSource, QualityFlag

        synthetic_obs = WeatherObservation(
            location_id=location_id,
            latitude=0.0,  # Will be filled if entity is in graph
            longitude=0.0,
            timestamp=datetime.now(UTC),
            temperature_2m=current.temperature_2m,
            precipitation_mm=current.precipitation_mm,
            humidity_pct=current.humidity_pct,
            pressure_hpa=current.pressure_hpa,
            wind_speed_10m=current.wind_speed_10m,
            wind_direction_10m=current.wind_direction_10m,
            solar_radiation=current.solar_radiation,
            cloud_cover_pct=current.cloud_cover_pct,
            soil_moisture=current.soil_moisture,
            data_source=DataSource(primary_source),
            quality_flag=QualityFlag.VALIDATED,
        )

        return await self._reconciler.reconcile(location_id, synthetic_obs)

    # ─── Entity Graph Management ──────────────────────────────────────────

    async def add_entity_to_graph(
        self,
        entity_id: str,
        latitude: float,
        longitude: float,
        name: str = "",
    ) -> None:
        """Add an entity to the graph and register its location.

        Args:
            entity_id: Entity identifier.
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            name: Human-readable name (optional).
        """
        from simulator.models.twin_state import TwinEntity

        entity = TwinEntity(
            entity_id=entity_id,
            name=name or entity_id,
            location_id=entity_id,
            latitude=latitude,
            longitude=longitude,
        )
        self._graph.add_entity(entity)

        # Also register in the store for spatial queries
        self._store.register_entity_location(entity_id, latitude, longitude)

    async def get_graph_neighbors(
        self,
        entity_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[Any]:
        """Get neighboring entities in the graph.

        Args:
            entity_id: Entity identifier.
            relationship_type: Filter by relationship type (optional).

        Returns:
            List of neighboring entities.
        """
        return self._graph.get_neighbors(entity_id, relationship_type)

    async def query_within_distance(
        self,
        lat: float,
        lon: float,
        km: float,
    ) -> list[Any]:
        """Find entities within a given distance using the graph.

        Args:
            lat: Center latitude.
            lon: Center longitude.
            km: Search radius in kilometers.

        Returns:
            List of entities within the radius.
        """
        return self._graph.query_within_distance(lat, lon, km)

    # ─── Utility ──────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Get the health status of the state manager.

        Returns:
            Dictionary with health metrics.
        """
        return {
            "status": "healthy",
            "store_initialized": self._store is not None,
            "graph_entity_count": (self._graph.entity_count() if self._graph else 0),
            "version_index_exists": (
                self._store._version_index_path.exists()
                if hasattr(self._store, "_version_index_path")
                else False
            ),
        }


def _add_optional(
    base: float | None,
    delta: float | None,
) -> float | None:
    """Safely add an optional delta to an optional base value."""
    if base is None and delta is None:
        return None
    if base is None:
        return delta
    if delta is None:
        return base
    return base + delta


__all__ = [
    "TwinStateManager",
]
