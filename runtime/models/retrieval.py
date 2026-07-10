"""Retrieval models for the Retrieval Stage.

Represents retrieval queries, chunks, results, and citations.
All models are domain-agnostic — no domain-specific concepts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalQuery:
    """A retrieval request submitted to the Retrieval Stage."""

    query: str
    top_k: int = 5
    filters: dict[str, Any] = field(default_factory=dict)
    min_score: float = 0.3
    include_metadata: bool = True
    query_id: str = field(default_factory=lambda: f"rq_{uuid.uuid4().hex[:12]}")


@dataclass
class Chunk:
    """A single chunk retrieved from a knowledge source."""

    text: str
    source: str
    score: float = 0.0
    chunk_id: str = field(default_factory=lambda: f"ch_{uuid.uuid4().hex[:12]}")
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_distance: float | None = None

    def passed_filter(self, min_score: float) -> bool:
        return self.score >= min_score


@dataclass
class Citation:
    """A citation extracted from a retrieval result."""

    source: str
    text: str
    relevance: float = 1.0
    chunk_id: str | None = None
    url: str | None = None
    page: int | None = None


@dataclass
class RetrievalResult:
    """The complete result of a retrieval operation.

    Contains all chunks, citations, and the original query.
    """

    query: str
    chunks: list[Chunk] = field(default_factory=list)
    total_results: int = 0
    latency_ms: float = 0.0
    query_id: str = field(default_factory=lambda: f"rr_{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def top_chunks(self) -> list[Chunk]:
        """Return chunks sorted by score descending."""
        return sorted(self.chunks, key=lambda c: c.score, reverse=True)

    @property
    def citations(self) -> list[Citation]:
        """Extract citations from top chunks."""
        return [
            Citation(
                source=c.source,
                text=c.text[:200],
                relevance=c.score,
                chunk_id=c.chunk_id,
            )
            for c in self.top_chunks[:10]
            if c.score > 0.3
        ]

    def passed(self, min_score: float = 0.3) -> bool:
        """Whether any chunks passed the minimum score threshold."""
        return any(c.score >= min_score for c in self.chunks)
