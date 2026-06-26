"""Knowledge Base & Retrieval-Augmented Generation (RAG) module.

Provides document ingestion, chunking, embedding, vector storage,
semantic search, and context retrieval for the Climate Copilot.
"""

from knowledge.api.search_api import KnowledgeAPI
from knowledge.models import (
    Chunk,
    Document,
    IndexingResult,
    RetrievalContext,
    SearchResult,
    SourceInfo,
)
from knowledge.pipelines.indexing_pipeline import IndexingPipeline
from knowledge.retriever.semantic_search import SemanticSearch
from knowledge.vector_store.faiss_store import FAISSStore

__all__ = [
    "KnowledgeAPI",
    "IndexingPipeline",
    "SemanticSearch",
    "FAISSStore",
    "Document",
    "Chunk",
    "SearchResult",
    "RetrievalContext",
    "IndexingResult",
    "SourceInfo",
]
