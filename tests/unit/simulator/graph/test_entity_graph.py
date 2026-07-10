import pytest

from simulator.graph.entity_graph import (
    RelationshipType,
    TwinEntityGraph,
    _haversine_distance,
)
from simulator.models.twin_state import TwinEntity


def make_entity(eid="e1", name="Entity 1", lat=0.0, lon=0.0):
    return TwinEntity(
        entity_id=eid,
        name=name,
        location_id=eid,
        latitude=lat,
        longitude=lon,
        district="Test",
        state="Test",
        country="IN",
    )


class TestHaversineDistance:
    def test_zero_distance(self):
        assert _haversine_distance(0, 0, 0, 0) == 0.0

    def test_known_distance(self):
        d = _haversine_distance(52.5200, 13.4050, 48.8566, 2.3522)
        assert abs(d - 878) < 10

    def test_antipodal(self):
        d = _haversine_distance(0, 0, 0, 180)
        assert abs(d - 20015) < 100

    def test_symmetry(self):
        d1 = _haversine_distance(10, 20, 30, 40)
        d2 = _haversine_distance(30, 40, 10, 20)
        assert abs(d1 - d2) < 0.001


class TestEntityCRUD:
    def test_add_entity(self):
        g = TwinEntityGraph()
        e = make_entity()
        g.add_entity(e)
        assert g.entity_count() == 1

    def test_add_duplicate_raises(self):
        g = TwinEntityGraph()
        e = make_entity()
        g.add_entity(e)
        with pytest.raises(ValueError, match="already exists"):
            g.add_entity(make_entity())

    def test_remove_entity(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity())
        g.remove_entity("e1")
        assert g.entity_count() == 0

    def test_remove_nonexistent_raises(self):
        g = TwinEntityGraph()
        with pytest.raises(KeyError, match="not found"):
            g.remove_entity("nonexistent")

    def test_get_entity(self):
        g = TwinEntityGraph()
        e = make_entity()
        g.add_entity(e)
        assert g.get_entity("e1") is e
        assert g.get_entity("nonexistent") is None

    def test_list_entities(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1", "E1"))
        g.add_entity(make_entity("e2", "E2"))
        entities = g.list_entities()
        assert len(entities) == 2

    def test_clear(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity())
        g.add_entity(make_entity("e2", "E2"))
        g.clear()
        assert g.entity_count() == 0
        assert g.get_relationship_count() == 0


class TestRelationships:
    def test_add_relationship(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1", "E1"))
        g.add_entity(make_entity("e2", "E2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        assert g.get_relationship_count() == 1

    def test_add_relationship_missing_source(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e2", "E2"))
        with pytest.raises(KeyError, match="Source"):
            g.add_relationship("e1", "e2", RelationshipType.CONTAINS)

    def test_add_relationship_missing_target(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1", "E1"))
        with pytest.raises(KeyError, match="Target"):
            g.add_relationship("e1", "e2", RelationshipType.CONTAINS)

    def test_add_duplicate_relationship_raises(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        with pytest.raises(ValueError, match="already exists"):
            g.add_relationship("e1", "e2", RelationshipType.CONTAINS)

    def test_remove_relationship_by_type(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.remove_relationship("e1", "e2", RelationshipType.CONTAINS)
        assert g.get_relationship_count() == 0

    def test_remove_all_relationships(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.add_relationship("e1", "e2", RelationshipType.AFFECTS)
        g.remove_relationship("e1", "e2")
        assert g.get_relationship_count() == 0

    def test_remove_nonexistent_source(self):
        g = TwinEntityGraph()
        with pytest.raises(KeyError):
            g.remove_relationship("e1", "e2")


class TestQuery:
    def test_get_neighbors(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.add_relationship("e1", "e3", RelationshipType.AFFECTS)
        neighbors = g.get_neighbors("e1")
        assert len(neighbors) == 2

    def test_get_neighbors_filtered(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.add_relationship("e1", "e2", RelationshipType.AFFECTS)
        neighbors = g.get_neighbors("e1", RelationshipType.CONTAINS)
        assert len(neighbors) == 1

    def test_get_neighbors_nonexistent(self):
        g = TwinEntityGraph()
        assert g.get_neighbors("nonexistent") == []

    def test_get_relationships(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=2.0)
        rels = g.get_relationships("e1")
        assert len(rels) == 1
        assert rels[0] == ("e2", RelationshipType.CONTAINS, 2.0)

    def test_get_relationships_nonexistent(self):
        g = TwinEntityGraph()
        assert g.get_relationships("nonexistent") == []


class TestPathfinding:
    def test_shortest_path_direct(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=1.0)
        path = g.get_shortest_path("e1", "e2")
        assert len(path) == 2

    def test_shortest_path_self(self):
        g = TwinEntityGraph()
        e = make_entity()
        g.add_entity(e)
        path = g.get_shortest_path("e1", "e1")
        assert len(path) == 1
        assert path[0] is e

    def test_shortest_path_no_path(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        path = g.get_shortest_path("e1", "e2")
        assert path == []

    def test_shortest_path_nonexistent(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        assert g.get_shortest_path("e1", "nonexistent") == []
        assert g.get_shortest_path("nonexistent", "e1") == []

    def test_shortest_path_multi_hop(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e2", "e3", RelationshipType.CONTAINS, weight=1.0)
        path = g.get_shortest_path("e1", "e3")
        assert len(path) == 3

    def test_shortest_path_chooses_min_weight(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_relationship("e1", "e3", RelationshipType.CONTAINS, weight=10.0)
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e2", "e3", RelationshipType.CONTAINS, weight=1.0)
        path = g.get_shortest_path("e1", "e3")
        assert len(path) == 3


class TestSpatialQuery:
    def test_query_within_distance(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1", lat=12.97, lon=77.59))
        g.add_entity(make_entity("e2", lat=13.00, lon=77.60))
        g.add_entity(make_entity("e3", lat=50.00, lon=10.00))
        results = g.query_within_distance(12.97, 77.59, 50)
        assert len(results) >= 2

    def test_query_within_distance_none(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1", lat=12.97, lon=77.59))
        results = g.query_within_distance(50.0, 10.0, 1)
        assert len(results) == 0

    def test_query_within_distance_empty(self):
        g = TwinEntityGraph()
        assert g.query_within_distance(0, 0, 100) == []


class TestEdgeCases:
    def test_remove_entity_cleans_edges(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.remove_entity("e2")
        assert g.get_relationship_count() == 0
        rels = g.get_relationships("e1")
        assert rels == []

    def test_add_relationship_after_remove(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.remove_relationship("e1", "e2")
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        assert g.get_relationship_count() == 1

    def test_multiple_relationship_types(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.add_relationship("e1", "e2", RelationshipType.AFFECTS)
        g.add_relationship("e1", "e2", RelationshipType.CORRELATED)
        assert g.get_relationship_count() == 3


class TestRelationshipType:
    def test_values(self):
        assert RelationshipType.CONTAINS.value == "contains"
        assert RelationshipType.AFFECTS.value == "affects"
        assert RelationshipType.CORRELATED.value == "correlated"
        assert RelationshipType.DISTANCE_BASED.value == "distance_based"
        assert RelationshipType.MONITORED_BY.value == "monitored_by"
        assert RelationshipType.FEEDS_INTO.value == "feeds_into"


class TestRemoveEntityEdgeCases:
    def test_remove_entity_with_outgoing_edges(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS)
        g.remove_entity("e1")
        assert g.get_entity("e1") is None
        assert g.get_relationship_count() == 0

    def test_remove_relationship_missing_target(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        with pytest.raises(KeyError, match="Target"):
            g.remove_relationship("e1", "nonexistent", RelationshipType.CONTAINS)


class TestGetShortestPathVisited:
    def test_shortest_path_with_multiple_routes_visits_nodes(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_entity(make_entity("e4"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=5.0)
        g.add_relationship("e1", "e3", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e3", "e2", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e2", "e4", RelationshipType.CONTAINS, weight=1.0)
        path = g.get_shortest_path("e1", "e4")
        assert len(path) > 0
        assert path[-1].entity_id == "e4"

    def test_shortest_path_exhausts_pq_no_target(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_entity(make_entity("e4"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=5.0)
        g.add_relationship("e1", "e3", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e3", "e2", RelationshipType.CONTAINS, weight=1.0)
        path = g.get_shortest_path("e1", "e4")
        assert path == []

    def test_shortest_path_with_cycle_visits_nodes(self):
        g = TwinEntityGraph()
        g.add_entity(make_entity("e1"))
        g.add_entity(make_entity("e2"))
        g.add_entity(make_entity("e3"))
        g.add_relationship("e1", "e2", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e2", "e3", RelationshipType.CONTAINS, weight=1.0)
        g.add_relationship("e2", "e1", RelationshipType.CONTAINS, weight=0.1)
        path = g.get_shortest_path("e1", "e3")
        assert len(path) == 3


class TestGetEntityCount:
    def test_get_entity_count_public_method(self):
        g = TwinEntityGraph()
        assert g.get_entity_count() == 0
        g.add_entity(make_entity("e1"))
        assert g.get_entity_count() == 1
