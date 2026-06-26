"""KnowledgeAPI — public contract for the RAG Knowledge Base.

Exposes indexing, search, retrieval, and source management
operations for downstream consumers (Copilot, Dashboard, Reports).
"""

from typing import Any

from knowledge.config_loader import load_rag_config
from knowledge.embeddings import EmbeddingModel
from knowledge.models import IndexingResult, RetrievalContext, SearchResult
from knowledge.pipelines import IndexingPipeline
from knowledge.retriever import SemanticSearch
from knowledge.vector_store import FAISSStore


class KnowledgeAPI:
    """High-level API for the RAG Knowledge Base.

    Provides convenience wrappers around the pipeline, search,
    and vector store for easy integration.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_rag_config()
        self.config = config
        rag_cfg = config.get("rag", {})
        vs_cfg = config.get("vector_store", {})
        self.vector_store = FAISSStore(
            index_path=vs_cfg.get("index_path", "knowledge/vector_store/index.faiss"),
            metadata_path=vs_cfg.get("metadata_path", "knowledge/vector_store/metadata.pkl"),
            dimension=rag_cfg.get("embedding_dimension", 384),
        )
        self.embedding_model = EmbeddingModel(config)
        self.pipeline = IndexingPipeline(config)
        self.pipeline.vector_store = self.vector_store
        self.searcher = SemanticSearch(
            vector_store=self.vector_store,
            embedding_model=self.embedding_model,
            config=config,
        )

    def index_document(self, file_path: str, **metadata: Any) -> IndexingResult:
        """Index a single document.

        Args:
            file_path: Path to the document file.
            **metadata: Optional metadata overrides.

        Returns:
            IndexingResult with status.
        """
        return self.pipeline.index_document(file_path, **metadata)

    def index_directory(self, directory: str, recursive: bool = True, **metadata: Any) -> list[IndexingResult]:
        """Index all supported documents in a directory.

        Args:
            directory: Directory path.
            recursive: Include subdirectories.
            **metadata: Metadata for all documents.

        Returns:
            List of IndexingResult.
        """
        return self.pipeline.index_directory(directory, recursive=recursive, **metadata)

    def delete_document(self, document_id: str) -> int:
        """Remove a document and its chunks from the index.

        Args:
            document_id: Document ID to remove.

        Returns:
            Number of chunks removed.
        """
        return self.vector_store.delete_document(document_id)

    def search(self, query: str, top_k: int | None = None, score_threshold: float | None = None) -> list[SearchResult]:
        """Semantic search over the knowledge base.

        Args:
            query: Natural language query.
            top_k: Max results.
            score_threshold: Minimum similarity score.

        Returns:
            List of SearchResult.
        """
        return self.searcher.search(query, top_k=top_k, score_threshold=score_threshold)

    def semantic_search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Alias for search()."""
        return self.search(query, top_k=top_k)

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
            score_threshold: Minimum similarity score.
            metadata_filter: Optional filter dict.

        Returns:
            RetrievalContext with results and context text.
        """
        return self.searcher.retrieve_context(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
        )

    def list_sources(self) -> list[dict[str, Any]]:
        """List all indexed document sources with chunk counts."""
        return self.vector_store.list_sources()

    def rebuild_index(self) -> None:
        """Clear and rebuild the entire index."""
        self.vector_store.clear()

    def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the indexed knowledge base."""
        sources = self.list_sources()
        total_chunks = sum(s.get("chunk_count", 0) for s in sources)
        categories: dict[str, int] = {}
        for s in sources:
            cat = s.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_documents": len(sources),
            "total_chunks": total_chunks,
            "categories": categories,
            "sources": sources,
        }
