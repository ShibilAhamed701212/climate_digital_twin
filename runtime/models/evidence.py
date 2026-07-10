"""Evidence, Fact, and Evidence Graph models.

Evidence is the universal currency of the Runtime.
Every provider output becomes an immutable Evidence object.
The Evidence Graph tracks relationships between evidence items.
Facts are structured subject-predicate-object triples.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceSource(Enum):
    """Origin of an evidence item."""

    PROVIDER = "provider"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    INFERENCE = "inference"
    USER_INPUT = "user_input"
    SYSTEM = "system"


class EvidenceRelationship(Enum):
    """Relationship types in the Evidence Graph."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    RETRIEVED_FROM = "retrieved_from"
    GENERATED_BY = "generated_by"
    CITED_BY = "cited_by"
    CORROBORATES = "corroborates"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True)
class Provenance:
    """Origin tracking for an evidence item."""

    source: str
    capability: str | None = None
    provider_id: str | None = None
    step_id: str | None = None
    method: str | None = None


@dataclass(frozen=True)
class Citation:
    """A citation backing an evidence item."""

    source: str
    text: str
    relevance: float = 1.0
    url: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class Evidence:
    """An immutable piece of evidence.

    Once created, an Evidence object must not be mutated.
    All fields are set at construction time.
    """

    id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:12]}")
    source: EvidenceSource = EvidenceSource.PROVIDER
    capability: str | None = None
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    provenance: Provenance | None = None
    citations: list[Citation] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_confidence(self, confidence: float) -> Evidence:
        """Return a new Evidence with updated confidence (immutable pattern)."""
        return Evidence(
            id=self.id,
            source=self.source,
            capability=self.capability,
            timestamp=self.timestamp,
            confidence=confidence,
            provenance=self.provenance,
            citations=self.citations,
            payload=self.payload,
            metadata=self.metadata,
        )

    def with_citation(self, citation: Citation) -> Evidence:
        """Return a new Evidence with an additional citation."""
        return Evidence(
            id=self.id,
            source=self.source,
            capability=self.capability,
            timestamp=self.timestamp,
            confidence=self.confidence,
            provenance=self.provenance,
            citations=self.citations + [citation],
            payload=self.payload,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class Fact:
    """A structured fact stored in Memory.

    Represents a subject-predicate-object triple with confidence and provenance.
    Facts are the building blocks of structured Memory — never raw text.
    """

    id: str = field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:12]}")
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    confidence: float = 1.0
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    ttl: int | None = None  # Time-to-live in seconds, None = permanent
    metadata: dict[str, Any] = field(default_factory=dict)

    def expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


@dataclass
class ConflictRecord:
    """Records a detected conflict between two evidence items."""

    evidence_a_id: str
    evidence_b_id: str
    field: str
    value_a: Any
    value_b: Any
    severity: str = "warning"  # "warning", "error"
    resolution: str | None = None


class EvidenceGraph:
    """Directed graph tracking relationships between Evidence items.

    Supports, contradicts, derived_from, retrieved_from, generated_by.
    Reasoning operates on the graph, not isolated outputs.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Evidence] = {}
        self._edges: list[tuple[str, str, EvidenceRelationship]] = []

    def add_evidence(self, evidence: Evidence) -> None:
        self._nodes[evidence.id] = evidence

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship: EvidenceRelationship,
    ) -> None:
        if from_id in self._nodes and to_id in self._nodes:
            self._edges.append((from_id, to_id, relationship))

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        return self._nodes.get(evidence_id)

    def get_all_evidence(self) -> list[Evidence]:
        return list(self._nodes.values())

    def get_relationships(
        self,
        evidence_id: str,
        relationship_type: EvidenceRelationship | None = None,
    ) -> list[tuple[str, str, EvidenceRelationship]]:
        matching = []
        for f, t, r in self._edges:
            if (f == evidence_id or t == evidence_id) and (
                relationship_type is None or r == relationship_type
            ):
                matching.append((f, t, r))
        return matching

    def get_supported_by(self, evidence_id: str) -> list[Evidence]:
        supporting = []
        for f, t, r in self._edges:
            if t == evidence_id and r == EvidenceRelationship.SUPPORTS:
                ev = self._nodes.get(f)
                if ev:
                    supporting.append(ev)
        return supporting

    def get_contradicted_by(self, evidence_id: str) -> list[Evidence]:
        contradicting = []
        for f, t, r in self._edges:
            if t == evidence_id and r == EvidenceRelationship.CONTRADICTS:
                ev = self._nodes.get(f)
                if ev:
                    contradicting.append(ev)
        return contradicting

    def get_derived_evidence(self, source_id: str) -> list[Evidence]:
        derived = []
        for f, t, r in self._edges:
            if f == source_id and r == EvidenceRelationship.DERIVED_FROM:
                ev = self._nodes.get(t)
                if ev:
                    derived.append(ev)
        return derived

    def merge(self, other: EvidenceGraph) -> None:
        """Merge another graph into this one."""
        for ev in other.get_all_evidence():
            if ev.id not in self._nodes:
                self._nodes[ev.id] = ev
        for f, t, r in other._edges:
            if (f, t, r) not in self._edges:
                self._edges.append((f, t, r))

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)
