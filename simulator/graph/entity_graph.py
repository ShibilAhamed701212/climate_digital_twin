"""Entity relationship graph for Digital Twin entities.

Manages relationships between twin entities for spatial and dependency
queries, including containment hierarchies, correlation links, and
distance-based proximity.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from enum import StrEnum
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt

from simulator.models.twin_state import TwinEntity

_logger = logging.getLogger(__name__)


class RelationshipType(StrEnum):
    """Types of relationships between twin entities."""

    CONTAINS = "contains"
    """District contains locations (hierarchical)."""

    AFFECTS = "affects"
    """Weather at one location affects another (e.g., upstream wind)."""

    CORRELATED = "correlated"
    """Climate variables are correlated between locations."""

    DISTANCE_BASED = "distance_based"
    """Nearby locations within a distance threshold."""

    MONITORED_BY = "monitored_by"
    """Location is monitored by a specific station/source."""

    FEEDS_INTO = "feeds_into"
    """Data flow direction (e.g., sensor -> aggregator)."""


# Earth radius in kilometers
_EARTH_RADIUS_KM = 6371.0


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two points in kilometers.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in kilometers.
    """
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return _EARTH_RADIUS_KM * c


class TwinEntityGraph:
    """A graph of twin entities and their relationships.

    Supports adding entities and relationships, querying neighbors,
    finding paths, and spatial proximity queries.

    Thread-safe for concurrent read operations. Writes should be
    serialized externally.
    """

    def __init__(self) -> None:
        """Initialize an empty entity graph."""
        self._entities: dict[str, TwinEntity] = {}
        self._adjacency: dict[str, dict[str, dict[RelationshipType, float]]] = defaultdict(
            lambda: defaultdict(dict)
        )

    # ─── Entity Management ────────────────────────────────────────────────

    def add_entity(self, entity: TwinEntity) -> None:
        """Add a twin entity to the graph.

        Args:
            entity: The twin entity to add.

        Raises:
            ValueError: If an entity with the same ID already exists.
        """
        if entity.entity_id in self._entities:
            raise ValueError(f"Entity '{entity.entity_id}' already exists in graph")
        self._entities[entity.entity_id] = entity
        _logger.debug("Added entity '%s' to graph", entity.entity_id)

    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity and all its relationships from the graph.

        Args:
            entity_id: The entity to remove.

        Raises:
            KeyError: If the entity does not exist.
        """
        if entity_id not in self._entities:
            raise KeyError(f"Entity '{entity_id}' not found in graph")

        del self._entities[entity_id]
        if entity_id in self._adjacency:
            del self._adjacency[entity_id]

        # Remove all edges pointing to this entity
        for neighbor in list(self._adjacency.keys()):
            if entity_id in self._adjacency[neighbor]:
                del self._adjacency[neighbor][entity_id]

        _logger.debug("Removed entity '%s' from graph", entity_id)

    def get_entity(self, entity_id: str) -> TwinEntity | None:
        """Get an entity by its ID.

        Args:
            entity_id: The entity identifier.

        Returns:
            The TwinEntity, or None if not found.
        """
        return self._entities.get(entity_id)

    def list_entities(self) -> list[TwinEntity]:
        """List all entities in the graph.

        Returns:
            List of all TwinEntity objects.
        """
        return list(self._entities.values())

    def entity_count(self) -> int:
        """Get the number of entities in the graph.

        Returns:
            Entity count.
        """
        return len(self._entities)

    # ─── Relationship Management ──────────────────────────────────────────

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationshipType,
        weight: float = 1.0,
    ) -> None:
        """Add a relationship between two entities.

        Both entities must already exist in the graph.

        Args:
            from_id: Source entity ID.
            to_id: Target entity ID.
            rel_type: Type of relationship.
            weight: Relationship weight (default 1.0).

        Raises:
            KeyError: If either entity does not exist.
            ValueError: If the relationship already exists.
        """
        if from_id not in self._entities:
            raise KeyError(f"Source entity '{from_id}' not found in graph")
        if to_id not in self._entities:
            raise KeyError(f"Target entity '{to_id}' not found in graph")

        if rel_type in self._adjacency[from_id][to_id]:
            raise ValueError(
                f"Relationship '{rel_type.value}' already exists from '{from_id}' to '{to_id}'"
            )

        self._adjacency[from_id][to_id][rel_type] = weight
        _logger.debug(
            "Added relationship '%s' from '%s' to '%s' (weight=%.2f)",
            rel_type.value,
            from_id,
            to_id,
            weight,
        )

    def remove_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationshipType | None = None,
    ) -> None:
        """Remove a relationship between two entities.

        Args:
            from_id: Source entity ID.
            to_id: Target entity ID.
            rel_type: Type of relationship to remove. If None, removes all.

        Raises:
            KeyError: If either entity does not exist.
        """
        if from_id not in self._entities:
            raise KeyError(f"Source entity '{from_id}' not found in graph")
        if to_id not in self._entities:
            raise KeyError(f"Target entity '{to_id}' not found in graph")

        if rel_type is not None:
            if to_id in self._adjacency[from_id] and rel_type in self._adjacency[from_id][to_id]:
                del self._adjacency[from_id][to_id][rel_type]
                if not self._adjacency[from_id][to_id]:
                    del self._adjacency[from_id][to_id]
        else:
            if to_id in self._adjacency[from_id]:
                del self._adjacency[from_id][to_id]

    # ─── Query Methods ────────────────────────────────────────────────────

    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[TwinEntity]:
        """Get neighboring entities connected to the given entity.

        Args:
            entity_id: The entity to find neighbors for.
            relationship_type: Optional filter by relationship type.

        Returns:
            List of neighboring TwinEntity objects.
        """
        if entity_id not in self._entities:
            return []

        neighbors: list[TwinEntity] = []
        neighbor_ids = list(self._adjacency[entity_id].keys())

        for nid in neighbor_ids:
            if relationship_type is not None:
                if relationship_type in self._adjacency[entity_id][nid]:
                    entity = self._entities.get(nid)
                    if entity:
                        neighbors.append(entity)
            else:
                entity = self._entities.get(nid)
                if entity:
                    neighbors.append(entity)

        return neighbors

    def get_shortest_path(
        self,
        from_id: str,
        to_id: str,
    ) -> list[TwinEntity]:
        """Find the shortest path between two entities using Dijkstra's algorithm.

        Uses relationship weights as edge costs.

        Args:
            from_id: Start entity ID.
            to_id: Target entity ID.

        Returns:
            List of TwinEntity objects forming the path (inclusive).
            Empty list if no path exists.
        """
        if from_id not in self._entities or to_id not in self._entities:
            return []
        if from_id == to_id:
            return [self._entities[from_id]]

        # Dijkstra
        distances: dict[str, float] = {from_id: 0.0}
        previous: dict[str, str | None] = {from_id: None}
        pq: list[tuple[float, str]] = [(0.0, from_id)]
        visited: set[str] = set()

        while pq:
            current_dist, current = heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == to_id:
                break

            for neighbor_id, rels in self._adjacency.get(current, {}).items():
                if neighbor_id in visited:
                    continue
                # Use minimum weight among all relationship types
                min_weight = min(rels.values()) if rels else 1.0
                new_dist = current_dist + min_weight

                if neighbor_id not in distances or new_dist < distances[neighbor_id]:
                    distances[neighbor_id] = new_dist
                    previous[neighbor_id] = current
                    heappush(pq, (new_dist, neighbor_id))

        # Reconstruct path
        if to_id not in previous:
            return []

        path: list[str] = []
        current: str | None = to_id
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()

        return [self._entities[eid] for eid in path]

    def query_within_distance(
        self,
        lat: float,
        lon: float,
        km: float,
    ) -> list[TwinEntity]:
        """Find all entities within a given distance of a point.

        Args:
            lat: Latitude of the center point in decimal degrees.
            lon: Longitude of the center point in decimal degrees.
            km: Search radius in kilometers.

        Returns:
            List of entities within the radius, sorted by distance (nearest first).
        """
        results: list[tuple[float, TwinEntity]] = []

        for entity in self._entities.values():
            distance = _haversine_distance(lat, lon, entity.latitude, entity.longitude)
            if distance <= km:
                results.append((distance, entity))

        results.sort(key=lambda x: x[0])
        return [entity for _, entity in results]

    def get_relationships(
        self,
        entity_id: str,
    ) -> list[tuple[str, RelationshipType, float]]:
        """Get all outgoing relationships for an entity.

        Args:
            entity_id: The entity to query.

        Returns:
            List of (target_id, relationship_type, weight) tuples.
        """
        if entity_id not in self._entities:
            return []

        edges: list[tuple[str, RelationshipType, float]] = []
        for neighbor_id, rels in self._adjacency[entity_id].items():
            for rel_type, weight in rels.items():
                edges.append((neighbor_id, rel_type, weight))
        return edges

    def get_entity_count(self) -> int:
        """Get the number of entities in the graph.

        Returns:
            Entity count.
        """
        return len(self._entities)

    def get_relationship_count(self) -> int:
        """Get the total number of relationships in the graph.

        Returns:
            Relationship count.
        """
        count = 0
        for from_id in self._adjacency:
            for to_id in self._adjacency[from_id]:
                count += len(self._adjacency[from_id][to_id])
        return count

    def clear(self) -> None:
        """Remove all entities and relationships from the graph."""
        self._entities.clear()
        self._adjacency.clear()
        _logger.info("Cleared all entities and relationships from graph")


__all__ = [
    "TwinEntityGraph",
    "RelationshipType",
]
