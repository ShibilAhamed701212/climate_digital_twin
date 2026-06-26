"""Semantic search engine with metadata filtering.

Combines vector similarity search with optional metadata
filters to retrieve relevant context chunks.
"""

import logging
import time
from typing import Any

from knowledge.config_loader import load_rag_config
from knowledge.embeddings import EmbeddingModel
from knowledge.models import RetrievalContext, SearchResult
from knowledge.vector_store import FAISSStore

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Semantic search over the knowledge base.

    Supports top-k retrieval, score threshold filtering,
    and optional metadata filtering.
    """

    def __init__(
        self,
        vector_store: FAISSStore | None = None,
        embedding_model: EmbeddingModel | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        if config is None:
            config = load_rag_config()
        ret_cfg = config.get("retrieval", {})
        self.top_k = ret_cfg.get("top_k", 5)
        self.score_threshold = ret_cfg.get("score_threshold", 0.5)
        self.enable_metadata_filtering = ret_cfg.get("enable_metadata_filtering", True)
        self.embedding_model = embedding_model or EmbeddingModel(config)
        if vector_store is not None:
            self.vector_store = vector_store
        else:
            emb_dim = self.embedding_model.dimension
            self.vector_store = FAISSStore(
                index_path=config.get("vector_store", {}).get("index_path", "knowledge/vector_store/index.faiss"),
                metadata_path=config.get("vector_store", {}).get("metadata_path", "knowledge/vector_store/metadata.pkl"),
                dimension=emb_dim,
            )

    def search(self, query: str, top_k: int | None = None, score_threshold: float | None = None) -> list[SearchResult]:
        """Perform semantic search.

        Args:
            query: Natural language query string.
            top_k: Max results (default from config).
            score_threshold: Minimum similarity score (default from config).

        Returns:
            List of SearchResult sorted by relevance.
        """
        k = top_k or self.top_k
        thresh = score_threshold if score_threshold is not None else self.score_threshold

        query_embedding = self.embedding_model.encode_single(query)
        results = self.vector_store.search(query_embedding, top_k=k)
        filtered = [r for r in results if r.score >= thresh]
        return filtered

    def retrieve_context(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RetrievalContext:
        """Retrieve context for a query with optional metadata filtering.

        Args:
            query: Natural language query.
            top_k: Max results.
            score_threshold: Minimum score.
            metadata_filter: Dict of metadata fields to filter on (e.g. {"category": "risk", "region": "Karnataka"}).

        Returns:
            RetrievalContext with results and assembled context text.
        """
        start = time.time()
        results = self.search(query, top_k=top_k, score_threshold=score_threshold)
        filtered_by_metadata = False

        if metadata_filter and self.enable_metadata_filtering:
            results = self._apply_metadata_filter(results, metadata_filter)
            filtered_by_metadata = True

        context_text = self._build_context_text(results)
        elapsed = (time.time() - start) * 1000

        return RetrievalContext(
            query=query,
            results=results,
            context_text=context_text,
            total_results=len(results),
            filtered_by_metadata=filtered_by_metadata,
            latency_ms=round(elapsed, 2),
        )

    def _apply_metadata_filter(self, results: list[SearchResult], filters: dict[str, Any]) -> list[SearchResult]:
        """Apply metadata filters to search results."""
        filtered = results
        for key, value in filters.items():
            if value is None:
                continue
            str_val = str(value).lower()
            filtered = [r for r in filtered if str(getattr(r, key, "")).lower() == str_val]
        return filtered

    def _build_context_text(self, results: list[SearchResult]) -> str:
        """Assemble search results into a single context string."""
        parts: list[str] = []
        for i, r in enumerate(results, 1):
            header = f"[{i}] {r.title} (Source: {r.source}, Category: {r.category}, Score: {r.score:.3f})"
            parts.append(header)
            parts.append(r.content)
            parts.append("---")
        return "\n".join(parts)
