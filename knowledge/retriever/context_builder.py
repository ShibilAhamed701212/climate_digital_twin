"""Context builder — assembles retrieved chunks into coherent context.

Prepares context for downstream use (Climate Copilot, dashboard, reports).
"""

from typing import Any

from knowledge.models import RetrievalContext


class ContextBuilder:
    """Builds structured context from retrieval results.

    Supports different context formats for different consumers
    (LLM prompts, dashboard display, report generation).
    """

    @staticmethod
    def build_llm_context(context: RetrievalContext, max_tokens: int = 2000) -> str:
        """Build a context string suitable for LLM consumption.

        Args:
            context: RetrievalContext from the search engine.
            max_tokens: Approximate token limit (by word count).

        Returns:
            Formatted context string.
        """
        lines: list[str] = [
            "## Retrieved Climate Information",
            f"Query: {context.query}",
            f"Found {context.total_results} relevant passages:",
            "",
        ]
        tokens_used = 0
        for r in context.results:
            entry = (
                f"### {r.title}\n"
                f"**Source:** {r.source} | **Category:** {r.category} | **Relevance:** {r.score:.2f}\n"
                f"**Region:** {r.region or 'N/A'}\n\n"
                f"{r.content}\n\n---\n"
            )
            entry_tokens = len(entry.split())
            if tokens_used + entry_tokens > max_tokens and tokens_used > 0:
                break
            lines.append(entry)
            tokens_used += entry_tokens

        return "\n".join(lines)

    @staticmethod
    def build_sectioned_context(context: RetrievalContext) -> dict[str, list[dict[str, Any]]]:
        """Group retrieval results by category.

        Returns a dict mapping category names to lists of result dicts.
        """
        sections: dict[str, list[dict[str, Any]]] = {}
        for r in context.results:
            cat = r.category or "general"
            if cat not in sections:
                sections[cat] = []
            sections[cat].append(r.to_dict())
        return sections

    @staticmethod
    def format_for_dashboard(context: RetrievalContext) -> dict[str, Any]:
        """Format context for dashboard display."""
        return {
            "query": context.query,
            "total_results": context.total_results,
            "latency_ms": context.latency_ms,
            "sections": ContextBuilder.build_sectioned_context(context),
            "context_text": context.context_text,
        }
