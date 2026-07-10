"""Reasoning models for the Reasoning Stage.

Supports deterministic (rule-based, graph-based) and LLM-assisted strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasoningStrategy(Enum):
    """Strategy used by the Reasoning Stage."""

    RULE_BASED = "rule_based"
    GRAPH_BASED = "graph_based"
    LLM_ASSISTED = "llm_assisted"
    HYBRID = "hybrid"


class ConclusionType(Enum):
    """Type of conclusion produced by reasoning."""

    DIRECT = "direct"  # Directly supported by evidence
    INFERRED = "inferred"  # Inferred from multiple evidence items
    DERIVED = "derived"  # Computed from evidence data
    AGGREGATED = "aggregated"  # Combined from multiple sources


@dataclass
class Conclusion:
    """A single conclusion produced by the Reasoning Stage."""

    statement: str
    confidence: float = 1.0
    conclusion_type: ConclusionType = ConclusionType.DIRECT
    supporting_evidence_ids: list[str] = field(default_factory=list)
    reasoning_path: str | None = None


@dataclass
class Assumption:
    """An assumption made during reasoning (not directly supported)."""

    statement: str
    confidence: float = 0.5
    reasoning: str | None = None


@dataclass
class Unknown:
    """Something that could not be determined."""

    question: str
    reason: str
    suggested_sources: list[str] = field(default_factory=list)


@dataclass
class ReasoningOutput:
    """Complete output of the Reasoning Stage.

    Contains conclusions, assumptions, unknowns, and metadata.
    The Response Stage consumes this — and only this — to generate the response.
    """

    conclusions: list[Conclusion] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    unknowns: list[Unknown] = field(default_factory=list)
    strategy: ReasoningStrategy = ReasoningStrategy.RULE_BASED
    confidence: float = 1.0
    reasoning_trace: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_conclusions(self) -> bool:
        return len(self.conclusions) > 0

    @property
    def has_unknowns(self) -> bool:
        return len(self.unknowns) > 0

    def get_statements(self) -> list[str]:
        return [c.statement for c in self.conclusions]
