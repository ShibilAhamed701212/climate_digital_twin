"""Runtime event type constants.

Events use past tense — they describe completed facts.
The Event Bus is never used as a command bus.
"""

# Memory lifecycle
MEMORY_LOADED = "memory.loaded"
MEMORY_STORE_UPDATED = "memory.store.updated"
MEMORY_FACT_RETRIEVED = "memory.fact.retrieved"

# Retrieval lifecycle
RETRIEVAL_STARTED = "retrieval.started"
RETRIEVAL_COMPLETED = "retrieval.completed"
RETRIEVAL_CHUNK_RANKED = "retrieval.chunk.ranked"

# Evidence lifecycle
EVIDENCE_AGGREGATED = "evidence.aggregated"
EVIDENCE_CONFLICT_DETECTED = "evidence.conflict.detected"
EVIDENCE_GRAPH_UPDATED = "evidence.graph.updated"

# Grounding lifecycle
GROUNDING_STARTED = "grounding.started"
GROUNDING_COMPLETED = "grounding.completed"
GROUNDING_UNSUPPORTED_DETECTED = "grounding.unsupported.detected"

# Reasoning lifecycle
REASONING_STARTED = "reasoning.started"
REASONING_COMPLETED = "reasoning.completed"
REASONING_STRATEGY_USED = "reasoning.strategy.used"

# Verification lifecycle (Runtime-level)
VERIFICATION_PASSED = "verification.passed"
VERIFICATION_FAILED = "verification.failed"
VERIFICATION_EVIDENCE_CHECKED = "verification.evidence.checked"

# Pipeline lifecycle (Runtime-level)
PIPELINE_EVIDENCE_COMPLETED = "pipeline.evidence.completed"

ALL_RUNTIME_EVENT_TYPES = [
    MEMORY_LOADED,
    MEMORY_STORE_UPDATED,
    MEMORY_FACT_RETRIEVED,
    RETRIEVAL_STARTED,
    RETRIEVAL_COMPLETED,
    RETRIEVAL_CHUNK_RANKED,
    EVIDENCE_AGGREGATED,
    EVIDENCE_CONFLICT_DETECTED,
    EVIDENCE_GRAPH_UPDATED,
    GROUNDING_STARTED,
    GROUNDING_COMPLETED,
    GROUNDING_UNSUPPORTED_DETECTED,
    REASONING_STARTED,
    REASONING_COMPLETED,
    REASONING_STRATEGY_USED,
    VERIFICATION_PASSED,
    VERIFICATION_FAILED,
    VERIFICATION_EVIDENCE_CHECKED,
    PIPELINE_EVIDENCE_COMPLETED,
]
