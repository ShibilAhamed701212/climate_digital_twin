"""Runtime-native pipeline stages.

These stages are domain-agnostic and reusable by any plugin.
They implement evidence-centered processing:

- MemoryStage: load facts, preferences, conversation history
- RetrievalStage: hybrid retrieval, chunk ranking, citations
- EvidenceAggregationStage: merge, deduplicate, conflict detection
- GroundingStage: claim verification, evidence mapping
- ReasoningStage: deterministic/graph/rule reasoning
"""

from runtime.pipeline.stages.evidence_aggregation_stage import EvidenceAggregationStage
from runtime.pipeline.stages.grounding_stage import GroundingStage
from runtime.pipeline.stages.memory_stage import MemoryStage
from runtime.pipeline.stages.reasoning_stage import ReasoningStage
from runtime.pipeline.stages.retrieval_stage import RetrievalStage

__all__ = [
    "MemoryStage",
    "RetrievalStage",
    "EvidenceAggregationStage",
    "GroundingStage",
    "ReasoningStage",
]
