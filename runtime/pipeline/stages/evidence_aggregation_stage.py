"""EvidenceAggregationStage — convert provider results to structured Evidence.

Runtime-native stage. Domain-agnostic.
No domain rules or domain-specific logic.

Provider boundary enforcement:
- Raw provider data enters here
- Only structured Evidence objects leave

Responsibilities:
- Convert ProviderResults into list[Evidence]
- Merge evidence from multiple providers
- Deduplicate by content hash
- Detect conflicts between evidence items
- Calculate aggregate confidence
- Build the Evidence Graph with relationship tracking
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from runtime.events.definitions import (
    EVIDENCE_AGGREGATED,
    EVIDENCE_CONFLICT_DETECTED,
    EVIDENCE_GRAPH_UPDATED,
)
from runtime.models.events import Event as RuntimeEvent
from runtime.models.evidence import (
    Citation as EvidenceCitation,
)
from runtime.models.evidence import (
    ConflictRecord,
    Evidence,
    EvidenceGraph,
    EvidenceRelationship,
    EvidenceSource,
    Provenance,
)
from runtime.models.pipeline import ExecutionContext, PipelineStage


class EvidenceAggregationStage(PipelineStage):
    """Convert provider results to structured Evidence and build the Evidence Graph.

    Reads: stage_outputs["provider_results"] = ProviderResults (from ExecutionStage)
    Writes: blackboard keys under "evidence.*"
            stage_outputs["evidence_graph"] = EvidenceGraph
    """

    name = "evidence_aggregation"
    description = "Convert provider results to structured Evidence with graph"

    def __init__(self, dependency_map: dict[str, list[str]] | None = None) -> None:
        """Initialize with optional capability dependency map.

        The dependency map maps capability names to their dependency names.
        Used to build derived_from and supports relationships in the Evidence Graph.
        Defaults to empty — no automatic relationship building.
        """
        super().__init__()
        self._dependency_map = dependency_map or {}

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        provider_results = ctx.stage_outputs.get("provider_results")
        graph = EvidenceGraph()

        evidence_list: list[Evidence] = []

        if provider_results is None or not hasattr(provider_results, "items"):
            ctx.log_stage(self.name, "no_results", {"reason": "no provider_results"})
            ctx.blackboard.publish("evidence.list", evidence_list, self.name)
            ctx.blackboard.publish("evidence.graph", graph, self.name)
            ctx.stage_outputs["evidence_graph"] = graph
            ctx.add_metric("evidence.total", 0)
            return ctx

        items = getattr(provider_results, "items", [])
        start = time.time()

        for item in items:
            capability = getattr(item, "capability", "unknown")
            data = getattr(item, "data", {})
            success = getattr(item, "success", False)
            step_id = getattr(item, "step_id", "")

            if not success or not data:
                continue

            provenance = Provenance(
                source=f"provider:{capability}",
                capability=capability,
                step_id=step_id,
                provider_id=getattr(item, "metadata", {}).get("provider"),
            )

            # Create one Evidence per top-level key in the data
            for key, value in data.items():
                content_hash = self._hash_value({key: value})
                evidence = Evidence(
                    source=EvidenceSource.PROVIDER,
                    capability=capability,
                    confidence=getattr(item, "confidence", 0.8)
                    if hasattr(item, "confidence")
                    else 0.8,
                    provenance=provenance,
                    payload={key: value},
                    metadata={
                        "step_id": step_id,
                        "content_hash": content_hash,
                        "capability": capability,
                    },
                )

                # Extract citations from knowledge results
                if capability == "knowledge" and isinstance(value, list):
                    for r in value:
                        if isinstance(r, dict) and "text" in r:
                            evidence = evidence.with_citation(
                                EvidenceCitation(
                                    source=r.get("source", "Knowledge Base"),
                                    text=r.get("text", "")[:200],
                                    relevance=r.get("score", 0.5),
                                )
                            )

                evidence_list.append(evidence)
                graph.add_evidence(evidence)

        # Build relationships — evidence from capabilities that depend on others
        self._build_relationships(evidence_list, graph)

        # Detect conflicts between evidence from different capabilities
        conflicts = self._detect_conflicts(evidence_list)

        if conflicts:
            ctx.event_bus.publish(
                RuntimeEvent(
                    type=EVIDENCE_CONFLICT_DETECTED,
                    data={
                        "conflict_count": len(conflicts),
                        "conflicts": [
                            {
                                "a": c.evidence_a_id,
                                "b": c.evidence_b_id,
                                "field": c.field,
                            }
                            for c in conflicts
                        ],
                    },
                    source=self.name,
                    trace_id=ctx.runtime_context.trace_id,
                )
            )

        # Aggregate confidence
        if evidence_list:
            avg_confidence = sum(e.confidence for e in evidence_list) / len(
                evidence_list
            )
        else:
            avg_confidence = 1.0

        ctx.blackboard.publish("evidence.list", evidence_list, self.name)
        ctx.blackboard.publish("evidence.graph", graph, self.name)
        ctx.blackboard.publish("evidence.conflicts", conflicts, self.name)
        ctx.blackboard.publish(
            "evidence.aggregate_confidence", avg_confidence, self.name
        )
        ctx.blackboard.publish("evidence.total_count", len(evidence_list), self.name)
        ctx.stage_outputs["evidence_graph"] = graph

        ctx.add_metric("evidence.total", len(evidence_list))
        ctx.add_metric("evidence.conflicts", len(conflicts))
        ctx.add_metric("evidence.avg_confidence", avg_confidence)
        ctx.add_metric("evidence.latency_ms", (time.time() - start) * 1000)

        ctx.event_bus.publish(
            RuntimeEvent(
                type=EVIDENCE_AGGREGATED,
                data={
                    "evidence_count": len(evidence_list),
                    "conflicts": len(conflicts),
                    "avg_confidence": avg_confidence,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        ctx.event_bus.publish(
            RuntimeEvent(
                type=EVIDENCE_GRAPH_UPDATED,
                data={
                    "node_count": graph.node_count,
                    "edge_count": graph.edge_count,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        return ctx

    def _build_relationships(
        self,
        evidence_list: list[Evidence],
        graph: EvidenceGraph,
    ) -> None:
        """Build derived_from and supports relationships based on capability dependencies."""
        # Group evidence by capability
        by_capability: dict[str, list[Evidence]] = {}
        for ev in evidence_list:
            cap = ev.capability or "unknown"
            if cap not in by_capability:
                by_capability[cap] = []
            by_capability[cap].append(ev)

        # Use dependency map (injected via constructor) to build evidence relationships
        for cap, deps in self._dependency_map.items():
            cap_evidence = by_capability.get(cap, [])
            for dep in deps:
                dep_evidence = by_capability.get(dep, [])
                for ce in cap_evidence:
                    for de in dep_evidence:
                        graph.add_relationship(
                            ce.id, de.id, EvidenceRelationship.DERIVED_FROM
                        )
                        graph.add_relationship(
                            de.id, ce.id, EvidenceRelationship.SUPPORTS
                        )

    def _detect_conflicts(self, evidence_list: list[Evidence]) -> list[ConflictRecord]:
        """Detect conflicts between evidence items with overlapping payloads."""
        conflicts: list[ConflictRecord] = []

        # Compare each pair for conflicting values on same keys
        for i in range(len(evidence_list)):
            for j in range(i + 1, len(evidence_list)):
                a = evidence_list[i]
                b = evidence_list[j]

                # Only compare evidence from different capabilities
                if a.capability == b.capability:
                    continue

                # Check for conflicting values on overlapping payload keys
                a_keys = set(a.payload.keys())
                b_keys = set(b.payload.keys())
                common_keys = a_keys & b_keys

                for key in common_keys:
                    val_a = a.payload[key]
                    val_b = b.payload[key]
                    if val_a != val_b and val_a is not None and val_b is not None:
                        conflicts.append(
                            ConflictRecord(
                                evidence_a_id=a.id,
                                evidence_b_id=b.id,
                                field=key,
                                value_a=val_a,
                                value_b=val_b,
                                severity="warning",
                            )
                        )

        return conflicts

    def _hash_value(self, value: dict[str, Any]) -> str:
        """Create a stable content hash for deduplication."""
        raw = json.dumps(value, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
