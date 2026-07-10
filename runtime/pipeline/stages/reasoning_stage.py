"""ReasoningStage — deterministic, graph-based, and LLM-assisted reasoning.

Runtime-native stage. Domain-agnostic.
The Runtime owns reasoning infrastructure.
Plugins provide domain knowledge.

Responsibilities:
- Rule-based reasoning (preferred when sufficient)
- Graph-based reasoning over the Evidence Graph
- LLM-assisted reasoning (only when deterministic is insufficient)
- Produce structured conclusions, assumptions, and unknowns
- Expose ReasoningOutput for the Response Stage
"""

from __future__ import annotations

from runtime.events.definitions import (
    REASONING_COMPLETED,
    REASONING_STARTED,
    REASONING_STRATEGY_USED,
)
from runtime.models.events import Event as RuntimeEvent
from runtime.models.evidence import Evidence, EvidenceGraph
from runtime.models.pipeline import ExecutionContext, PipelineStage
from runtime.models.reasoning import (
    Assumption,
    Conclusion,
    ConclusionType,
    ReasoningOutput,
    ReasoningStrategy,
    Unknown,
)


class ReasoningStage(PipelineStage):
    """Perform reasoning over evidence to produce structured conclusions.

    Reads: blackboard "evidence.list", "evidence.graph"
           stage_outputs for context
    Writes: blackboard keys under "reasoning.*"
            stage_outputs["reasoning"] = ReasoningOutput

    Strategy preference: rule-based > graph-based > LLM-assisted
    """

    name = "reasoning"
    description = "Deterministic and graph-based reasoning over evidence"

    def __init__(self, prefer_deterministic: bool = True) -> None:
        super().__init__()
        self._prefer_deterministic = prefer_deterministic

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        ctx.event_bus.publish(
            RuntimeEvent(
                type=REASONING_STARTED,
                data={"strategy": "deterministic-first"},
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        # Get evidence and graph from blackboard
        evidence_list: list[Evidence] = []
        evidence_entry = ctx.blackboard.get("evidence.list")
        if evidence_entry and isinstance(evidence_entry.value, list):
            evidence_list = evidence_entry.value

        graph_entry = ctx.blackboard.get("evidence.graph")
        graph: EvidenceGraph | None = graph_entry.value if graph_entry else None

        reasoning_trace: list[str] = []
        conclusions: list[Conclusion] = []

        # Strategy 1: Rule-based reasoning (deterministic)
        rule_conclusions, trace = self._rule_based_reasoning(evidence_list, graph, ctx)
        conclusions.extend(rule_conclusions)
        reasoning_trace.extend(trace)

        if rule_conclusions:
            strategy = ReasoningStrategy.RULE_BASED
        else:
            # Strategy 2: Graph-based reasoning
            graph_conclusions, graph_trace = self._graph_based_reasoning(evidence_list, graph, ctx)
            conclusions.extend(graph_conclusions)
            reasoning_trace.extend(graph_trace)

            if graph_conclusions:
                strategy = ReasoningStrategy.GRAPH_BASED
            else:
                # Strategy 3: Simple aggregation (fallback deterministic)
                agg_conclusions, agg_trace = self._aggregate_reasoning(evidence_list, ctx)
                conclusions.extend(agg_conclusions)
                reasoning_trace.extend(agg_trace)
                strategy = ReasoningStrategy.RULE_BASED

        # Track assumptions and unknowns
        assumptions = self._build_assumptions(ctx)
        unknowns = self._build_unknowns(ctx)

        # Calculate overall confidence
        if conclusions:
            confidence = sum(c.confidence for c in conclusions) / len(conclusions)
        else:
            confidence = 1.0

        output = ReasoningOutput(
            conclusions=conclusions,
            assumptions=assumptions,
            unknowns=unknowns,
            strategy=strategy,
            confidence=confidence,
            reasoning_trace=reasoning_trace,
            metadata={
                "evidence_count": len(evidence_list),
                "graph_nodes": graph.node_count if graph else 0,
                "graph_edges": graph.edge_count if graph else 0,
            },
        )

        ctx.blackboard.publish("reasoning.output", output, self.name)
        ctx.blackboard.publish("reasoning.confidence", confidence, self.name)
        ctx.blackboard.publish("reasoning.conclusion_count", len(conclusions), self.name)
        ctx.blackboard.publish("reasoning.strategy", strategy.value, self.name)
        ctx.stage_outputs["reasoning"] = output

        ctx.add_metric("reasoning.conclusions", len(conclusions))
        ctx.add_metric("reasoning.assumptions", len(assumptions))
        ctx.add_metric("reasoning.unknowns", len(unknowns))
        ctx.add_metric("reasoning.confidence", confidence)
        ctx.add_metric("reasoning.strategy", strategy.value)

        ctx.event_bus.publish(
            RuntimeEvent(
                type=REASONING_STRATEGY_USED,
                data={
                    "strategy": strategy.value,
                    "conclusions": len(conclusions),
                    "assumptions": len(assumptions),
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        ctx.event_bus.publish(
            RuntimeEvent(
                type=REASONING_COMPLETED,
                data={
                    "conclusions": len(conclusions),
                    "assumptions": len(assumptions),
                    "unknowns": len(unknowns),
                    "confidence": confidence,
                    "strategy": strategy.value,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        return ctx

    def _rule_based_reasoning(
        self,
        evidence_list: list[Evidence],
        _graph: EvidenceGraph | None,
        _ctx: ExecutionContext,
    ) -> tuple[list[Conclusion], list[str]]:
        """Apply deterministic rules to evidence.

        Rules:
        1. If evidence has high confidence (>0.8), produce a direct conclusion
        2. If multiple evidence items agree, produce an aggregated conclusion
        3. If evidence contradicts, note the disagreement
        """
        conclusions: list[Conclusion] = []
        trace: list[str] = []

        # Rule 1: High-confidence evidence -> direct conclusions
        for ev in evidence_list:
            if ev.confidence >= 0.8:
                for key, value in ev.payload.items():
                    if isinstance(value, (str, int, float, bool)):
                        conclusion = Conclusion(
                            statement=f"{key}: {value}",
                            confidence=ev.confidence,
                            conclusion_type=ConclusionType.DIRECT,
                            supporting_evidence_ids=[ev.id],
                            reasoning_path=(
                                f"Rule 1: evidence confidence {ev.confidence:.2f} >= 0.8"
                            ),
                        )
                        conclusions.append(conclusion)
                        trace.append(f"Rule 1: Direct conclusion from {ev.id} ({ev.capability})")

        # Rule 2: Aggregate consistent values across evidence items
        grouped: dict[str, list[Evidence]] = {}
        for ev in evidence_list:
            for key in ev.payload:
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(ev)

        for key, group in grouped.items():
            if len(group) >= 2:
                values = [ev.payload[key] for ev in group]
                if all(v == values[0] for v in values if isinstance(v, (str, int, float, bool))):
                    conclusion = Conclusion(
                        statement=f"{key}: {values[0]}",
                        confidence=min(1.0, sum(ev.confidence for ev in group) / len(group) + 0.1),
                        conclusion_type=ConclusionType.AGGREGATED,
                        supporting_evidence_ids=[ev.id for ev in group],
                        reasoning_path=f"Rule 2: {len(group)} evidence items agree on '{key}'",
                    )
                    conclusions.append(conclusion)
                    trace.append(f"Rule 2: Aggregated '{key}' from {len(group)} evidence items")

        return conclusions, trace

    def _graph_based_reasoning(
        self,
        evidence_list: list[Evidence],
        graph: EvidenceGraph | None,
        _ctx: ExecutionContext,
    ) -> tuple[list[Conclusion], list[str]]:
        """Reason over the Evidence Graph using relationships.

        Uses supports/contradicts/derived_from edges to draw conclusions.
        """
        conclusions: list[Conclusion] = []
        trace: list[str] = []

        if graph is None or graph.node_count == 0:
            return conclusions, trace

        # For each node, if it has supporting evidence, produce a supported conclusion
        for ev in evidence_list:
            supported_by = graph.get_supported_by(ev.id)
            contradicted_by = graph.get_contradicted_by(ev.id)

            for key, value in ev.payload.items():
                if isinstance(value, (str, int, float, bool)):
                    statement = f"{key}: {value}"

                    if supported_by:
                        # Evidence is supported by other evidence
                        avg_support = sum(s.confidence for s in supported_by) / len(supported_by)
                        conclusion = Conclusion(
                            statement=statement,
                            confidence=min(1.0, ev.confidence * 1.1 + avg_support * 0.2),
                            conclusion_type=ConclusionType.DERIVED,
                            supporting_evidence_ids=[ev.id] + [s.id for s in supported_by],
                            reasoning_path=(
                                f"Graph: {ev.id} supported by {len(supported_by)} evidence items"
                            ),
                        )
                        conclusions.append(conclusion)
                        trace.append(
                            f"Graph: Supported conclusion '{statement}' from {len(supported_by)} sources"
                        )
                    elif not contradicted_by and ev.confidence > 0.5:
                        # Standalone but not contradicted
                        conclusion = Conclusion(
                            statement=statement,
                            confidence=ev.confidence * 0.9,
                            conclusion_type=ConclusionType.DIRECT,
                            supporting_evidence_ids=[ev.id],
                            reasoning_path="Graph: Standalone evidence, no contradictions",
                        )
                        conclusions.append(conclusion)
                        trace.append(f"Graph: Standalone conclusion '{statement}'")

        return conclusions, trace

    def _aggregate_reasoning(
        self,
        evidence_list: list[Evidence],
        _ctx: ExecutionContext,
    ) -> tuple[list[Conclusion], list[str]]:
        """Simple aggregation-based reasoning (fallback)."""
        conclusions: list[Conclusion] = []
        trace: list[str] = []

        if not evidence_list:
            return conclusions, trace

        for ev in evidence_list:
            for key, value in ev.payload.items():
                if isinstance(value, (str, int, float, bool)):
                    conclusions.append(
                        Conclusion(
                            statement=f"{key}: {value}",
                            confidence=ev.confidence * 0.8,
                            conclusion_type=ConclusionType.DIRECT,
                            supporting_evidence_ids=[ev.id],
                            reasoning_path="Aggregate: Direct evidence mapping",
                        )
                    )
                    trace.append(f"Aggregate: '{key}' from {ev.capability}")

        return conclusions, trace

    def _build_assumptions(self, ctx: ExecutionContext) -> list[Assumption]:
        """Build assumptions from pipeline context metadata."""
        assumptions: list[Assumption] = []

        # If planning created dependency chain, note it
        capability_selection = ctx.stage_outputs.get("capability_selection")
        if capability_selection and hasattr(capability_selection, "selected"):
            selected = getattr(capability_selection, "selected", [])
            if selected:
                assumptions.append(
                    Assumption(
                        statement=f"Capabilities used: {', '.join(selected)}",
                        confidence=0.9,
                        reasoning="Based on capability selection metadata",
                    )
                )

        return assumptions

    def _build_unknowns(self, ctx: ExecutionContext) -> list[Unknown]:
        """Build unknowns from pipeline errors or missing data."""
        unknowns: list[Unknown] = []

        # From execution errors
        for error in ctx.errors:
            unknowns.append(
                Unknown(
                    question=f"Error in {error.get('stage', 'unknown')}",
                    reason=error.get("error", "Unknown error"),
                    suggested_sources=["Retry with different parameters"],
                )
            )

        return unknowns
