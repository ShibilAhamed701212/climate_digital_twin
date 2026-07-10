"""RetrievalStage — hybrid retrieval, chunk ranking, filtering, citations, confidence.

Runtime-native stage. Domain-agnostic.
No domain-specific datasets, prompts, or logic.

This stage replaces all direct RAG client calls.
No raw chunks escape this stage — all output is structured Runtime models.
"""

from __future__ import annotations

import time
from typing import Any

from runtime.events.definitions import (
    RETRIEVAL_COMPLETED,
    RETRIEVAL_STARTED,
)
from runtime.models.events import Event as RuntimeEvent
from runtime.models.pipeline import ExecutionContext, PipelineStage
from runtime.models.provider import ProviderRequest
from runtime.models.retrieval import (
    Chunk,
    RetrievalQuery,
    RetrievalResult,
)


class RetrievalStage(PipelineStage):
    """Execute hybrid retrieval queries through knowledge providers.

    Responsibilities:
    - Create RetrievalQuery from pipeline context
    - Execute retrieval through providers registered for "knowledge" capability
    - Rank chunks by score
    - Apply minimum score filtering
    - Extract citations from top chunks
    - Expose structured RetrievalResult on the Blackboard

    Reads: stage_outputs["intent"] (for query context)
           stage_outputs["memory"] (for memory context to enrich queries)
    Writes: blackboard keys under "retrieval.*"
    """

    name = "retrieval"
    description = "Hybrid retrieval with ranking, filtering, and citations"

    def __init__(self, default_top_k: int = 5, min_score: float = 0.3) -> None:
        super().__init__()
        self._default_top_k = default_top_k
        self._min_score = min_score

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        # Determine what to retrieve from pipeline context
        query_text = self._get_query_text(ctx)
        if not query_text:
            ctx.log_stage(self.name, "no_query", {"reason": "no query text available"})
            ctx.blackboard.publish(
                "retrieval.result",
                RetrievalResult(query=""),
                self.name,
            )
            ctx.add_metric("retrieval.skipped", True)
            return ctx

        top_k = self._get_top_k(ctx)

        retrieval_query = RetrievalQuery(
            query=query_text,
            top_k=top_k,
            min_score=self._min_score,
        )

        ctx.event_bus.publish(
            RuntimeEvent(
                type=RETRIEVAL_STARTED,
                data={
                    "query": query_text[:100],
                    "top_k": top_k,
                    "min_score": self._min_score,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        start = time.time()

        # Execute retrieval via providers registered for "knowledge" capability
        provider = ctx.capability_router.select_provider("knowledge", ctx.provider_registry)

        result = RetrievalResult(query=query_text)

        if provider is None:
            ctx.log_stage(self.name, "no_provider", {"capability": "knowledge"})
            ctx.add_metric("retrieval.provider_found", False)
        else:
            ctx.add_metric("retrieval.provider_found", True)
            try:
                req = ProviderRequest(
                    capability="knowledge",
                    params={
                        "query": query_text,
                        "top_k": top_k,
                    },
                    context=ctx.runtime_context,
                )
                provider_result = await provider.execute(req)

                if provider_result.success:
                    chunks = self._extract_chunks(provider_result.data)
                    # Rank and filter
                    chunks.sort(key=lambda c: c.score, reverse=True)
                    chunks = [c for c in chunks if c.passed_filter(self._min_score)]
                    result = RetrievalResult(
                        query=query_text,
                        chunks=chunks,
                        total_results=len(chunks),
                        latency_ms=(time.time() - start) * 1000,
                    )
                    ctx.add_metric("retrieval.chunks_found", len(chunks))
                else:
                    ctx.log_stage(
                        self.name,
                        "provider_error",
                        {"error": provider_result.error},
                    )
                    ctx.add_metric("retrieval.error", True)

            except (ConnectionError, TimeoutError, ValueError) as e:
                ctx.log_stage(self.name, "error", {"error": str(e)})
                ctx.add_metric("retrieval.exception", True)

        result.latency_ms = (time.time() - start) * 1000

        # Write to Blackboard
        ctx.blackboard.publish("retrieval.result", result, self.name)
        ctx.blackboard.publish("retrieval.query", retrieval_query, self.name)
        ctx.blackboard.publish("retrieval.chunk_count", len(result.chunks), self.name)

        # Also store in stage_outputs for pipeline chaining
        ctx.stage_outputs["retrieval_result"] = result

        ctx.event_bus.publish(
            RuntimeEvent(
                type=RETRIEVAL_COMPLETED,
                data={
                    "query": query_text[:100],
                    "chunks": len(result.chunks),
                    "total_results": result.total_results,
                    "latency_ms": result.latency_ms,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        return ctx

    def _get_query_text(self, ctx: ExecutionContext) -> str:
        """Extract query text from pipeline context."""
        # Try intent context first
        intent = ctx.stage_outputs.get("intent")
        if intent:
            if hasattr(intent, "normalized_query") and intent.normalized_query:
                return intent.normalized_query
            if hasattr(intent, "query") and intent.query:
                return intent.query
        # Fall back to raw query on blackboard
        query_entry = ctx.blackboard.get("query.raw")
        if query_entry:
            return query_entry.value
        return ""

    def _get_top_k(self, ctx: ExecutionContext) -> int:
        """Determine top_k from context or use default."""
        intent = ctx.stage_outputs.get("intent")
        if intent and hasattr(intent, "entities") and intent.entities:
            entities = intent.entities
            if isinstance(entities, dict) and "top_k" in entities:
                return int(entities["top_k"])
        return self._default_top_k

    def _extract_chunks(self, data: dict[str, Any]) -> list[Chunk]:
        """Extract Chunk objects from provider response data."""
        chunks: list[Chunk] = []

        # Try common response formats
        results = data.get("results", data.get("chunks", data.get("items", [])))
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    chunk = Chunk(
                        text=item.get("text", item.get("content", str(item))),
                        source=item.get("source", item.get("document", "knowledge_base")),
                        score=float(item.get("score", item.get("relevance", 0.5))),
                        metadata={
                            k: v
                            for k, v in item.items()
                            if k not in ("text", "content", "source", "score", "relevance")
                        },
                    )
                    chunks.append(chunk)

        # Handle flat text response
        if not chunks and isinstance(data, dict):
            text = data.get("text", data.get("content", ""))
            if text:
                chunks.append(Chunk(text=str(text)[:500], source="provider", score=0.5))

        return chunks
