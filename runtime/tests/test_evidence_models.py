"""Tests for Evidence, Fact, and EvidenceGraph models."""

import time

import pytest

from runtime.models.evidence import (
    Citation,
    ConflictRecord,
    Evidence,
    EvidenceGraph,
    EvidenceRelationship,
    EvidenceSource,
    Fact,
    Provenance,
)


class TestEvidence:
    def test_create_evidence(self):
        ev = Evidence(
            source=EvidenceSource.PROVIDER,
            capability="forecast",
            confidence=0.9,
            payload={"temperature": 32.5},
        )
        assert ev.id.startswith("ev_")
        assert ev.source == EvidenceSource.PROVIDER
        assert ev.capability == "forecast"
        assert ev.confidence == 0.9
        assert ev.payload["temperature"] == 32.5

    def test_evidence_immutable_by_default(self):
        """Evidence should be frozen (immutable)."""
        ev = Evidence(payload={"temp": 25})
        with pytest.raises(AttributeError):
            ev.confidence = 0.5

    def test_evidence_with_confidence_returns_new_instance(self):
        ev = Evidence(confidence=0.7)
        ev2 = ev.with_confidence(0.95)
        assert ev.confidence == 0.7
        assert ev2.confidence == 0.95
        assert ev.id == ev2.id
        assert ev is not ev2

    def test_evidence_with_citation(self):
        ev = Evidence(payload={"result": "test"})
        cit = Citation(source="KB", text="test citation", relevance=0.8)
        ev2 = ev.with_citation(cit)
        assert len(ev.citations) == 0
        assert len(ev2.citations) == 1
        assert ev2.citations[0].source == "KB"
        assert ev2.citations[0].relevance == 0.8

    def test_evidence_with_provenance(self):
        prov = Provenance(
            source="forecast_api", capability="forecast", provider_id="forecast_v1"
        )
        ev = Evidence(provenance=prov)
        assert ev.provenance.source == "forecast_api"
        assert ev.provenance.capability == "forecast"

    def test_evidence_unique_ids(self):
        ev1 = Evidence()
        ev2 = Evidence()
        assert ev1.id != ev2.id


class TestFact:
    def test_create_fact(self):
        fact = Fact(subject="Bangalore", predicate="temperature", object_value=32.5)
        assert fact.subject == "Bangalore"
        assert fact.predicate == "temperature"
        assert fact.object_value == 32.5
        assert fact.confidence == 1.0

    def test_fact_expired(self):
        fact = Fact(subject="test", predicate="test", object_value=True, ttl=1)
        assert not fact.expired()
        time.sleep(1.1)
        assert fact.expired()

    def test_fact_no_expiry(self):
        fact = Fact(subject="test", predicate="test", object_value=True, ttl=None)
        assert not fact.expired()

    def test_fact_unique_ids(self):
        f1 = Fact(subject="a", predicate="b", object_value=1)
        f2 = Fact(subject="a", predicate="b", object_value=1)
        assert f1.id != f2.id


class TestEvidenceGraph:
    def test_empty_graph(self):
        graph = EvidenceGraph()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_evidence(self):
        graph = EvidenceGraph()
        ev = Evidence(payload={"test": 1})
        graph.add_evidence(ev)
        assert graph.node_count == 1
        assert graph.get_evidence(ev.id) is not None

    def test_add_relationship(self):
        graph = EvidenceGraph()
        ev1 = Evidence(payload={"a": 1})
        ev2 = Evidence(payload={"b": 2})
        graph.add_evidence(ev1)
        graph.add_evidence(ev2)
        graph.add_relationship(ev1.id, ev2.id, EvidenceRelationship.SUPPORTS)
        assert graph.edge_count == 1

    def test_get_supported_by(self):
        graph = EvidenceGraph()
        ev1 = Evidence(payload={"a": 1})
        ev2 = Evidence(payload={"b": 2})
        graph.add_evidence(ev1)
        graph.add_evidence(ev2)
        graph.add_relationship(ev1.id, ev2.id, EvidenceRelationship.SUPPORTS)
        supported = graph.get_supported_by(ev2.id)
        assert len(supported) == 1
        assert supported[0].id == ev1.id

    def test_get_contradicted_by(self):
        graph = EvidenceGraph()
        ev1 = Evidence(payload={"temp": 30})
        ev2 = Evidence(payload={"temp": 35})
        graph.add_evidence(ev1)
        graph.add_evidence(ev2)
        graph.add_relationship(ev1.id, ev2.id, EvidenceRelationship.CONTRADICTS)
        contradicted = graph.get_contradicted_by(ev2.id)
        assert len(contradicted) == 1

    def test_derived_evidence(self):
        graph = EvidenceGraph()
        source = Evidence(payload={"forecast": "rain"})
        derived = Evidence(payload={"risk": "high"})
        graph.add_evidence(source)
        graph.add_evidence(derived)
        graph.add_relationship(source.id, derived.id, EvidenceRelationship.DERIVED_FROM)
        derived_from = graph.get_derived_evidence(source.id)
        # DERIVED_FROM means derived is derived FROM source
        # So source -> DERIVED_FROM -> derived
        assert len(derived_from) == 1

    def test_merge_graphs(self):
        g1 = EvidenceGraph()
        g2 = EvidenceGraph()
        ev1 = Evidence(payload={"a": 1})
        ev2 = Evidence(payload={"b": 2})
        g1.add_evidence(ev1)
        g2.add_evidence(ev2)
        g1.merge(g2)
        assert g1.node_count == 2

    def test_get_all_evidence(self):
        graph = EvidenceGraph()
        ev1 = Evidence(payload={"a": 1})
        ev2 = Evidence(payload={"b": 2})
        graph.add_evidence(ev1)
        graph.add_evidence(ev2)
        all_ev = graph.get_all_evidence()
        assert len(all_ev) == 2

    def test_get_relationships_filtered(self):
        graph = EvidenceGraph()
        ev1 = Evidence(payload={"a": 1})
        ev2 = Evidence(payload={"b": 2})
        ev3 = Evidence(payload={"c": 3})
        graph.add_evidence(ev1)
        graph.add_evidence(ev2)
        graph.add_evidence(ev3)
        graph.add_relationship(ev1.id, ev2.id, EvidenceRelationship.SUPPORTS)
        graph.add_relationship(ev1.id, ev3.id, EvidenceRelationship.CONTRADICTS)

        supports = graph.get_relationships(ev2.id, EvidenceRelationship.SUPPORTS)
        contradicts = graph.get_relationships(ev3.id, EvidenceRelationship.CONTRADICTS)
        assert len(supports) == 1
        assert len(contradicts) == 1


class TestConflictRecord:
    def test_create_conflict(self):
        conflict = ConflictRecord(
            evidence_a_id="ev_001",
            evidence_b_id="ev_002",
            field="temperature",
            value_a=30,
            value_b=35,
        )
        assert conflict.field == "temperature"
        assert conflict.value_a == 30
        assert conflict.value_b == 35
        assert conflict.severity == "warning"
