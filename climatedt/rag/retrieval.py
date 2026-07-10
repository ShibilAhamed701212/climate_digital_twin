from typing import Any

from knowledge.embeddings.embedding_model import EmbeddingModel
from knowledge.models import SearchResult
from knowledge.retriever.semantic_search import SemanticSearch
from knowledge.vector_store.faiss_store import FAISSStore


class RetrievalService:
    def __init__(self, vector_store: FAISSStore) -> None:
        self._searcher = SemanticSearch(
            vector_store=vector_store,
            embedding_model=EmbeddingModel(),
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return self._searcher.search(query, top_k=top_k)

    def retrieve_context(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ):
        return self._searcher.retrieve_context(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
        )
