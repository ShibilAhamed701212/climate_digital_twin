"""Unit tests for semantic search and context builder."""

import tempfile

import pytest


def _real_embeddings_available() -> bool:
    try:
        from knowledge.embeddings.embedding_model import EmbeddingModel

        m = EmbeddingModel(model_name="all-MiniLM-L6-v2", dimension=384)
        return m.is_available()
    except Exception:
        return False


class _DummyEmbeddingModel:
    """Minimal embedding model using deterministic dummy vectors."""

    def __init__(self, dim: int = 384) -> None:
        self.dimension = dim

    def embed_query(self, text: str) -> list[float]:
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        return _get_dummy_embedding(text, self.dimension)

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        if isinstance(texts, str):
            texts = [texts]
        return [_get_dummy_embedding(t, self.dimension) for t in texts]

    def encode_single(self, text: str) -> list[float]:
        return self.embed_query(text)

    def is_available(self) -> bool:
        return True

    def get_dimension(self) -> int:
        return self.dimension


class TestSemanticSearch:
    @classmethod
    def setup_class(cls):
        if not _real_embeddings_available():
            pytest.skip("Real embedding model unavailable (torch DLL)")

    def test_search_empty_index(self):
        from knowledge.retriever import SemanticSearch

        with tempfile.TemporaryDirectory():
            searcher = SemanticSearch()
            results = searcher.search("test query", top_k=5)
            assert results == []

    def test_retrieve_context_empty(self):
        from knowledge.retriever import SemanticSearch

        with tempfile.TemporaryDirectory():
            searcher = SemanticSearch()
            ctx = searcher.retrieve_context("test", top_k=5)
            assert ctx.total_results == 0
            assert ctx.context_text == ""

    def test_retrieve_context_with_data(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            dim = 384
            store = FAISSStore(
                index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim
            )
            emb_vec = _get_dummy_embedding("rainfall data", dim)
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "general", "rainfall data", 1)],
                [emb_vec],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=_DummyEmbeddingModel(dim))
            ctx = searcher.retrieve_context("rainfall", top_k=5)
            assert ctx.total_results >= 1

    def test_metadata_filter(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            dim = 384
            store = FAISSStore(
                index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim
            )
            v1 = _get_dummy_embedding("flood risk data", dim)
            v2 = _get_dummy_embedding("temperature data", dim)
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "risk", "flood risk data", 1)],
                [v1],
            )
            store.add(
                [Chunk("c2", "d2", "Doc2", "src", "general", "temperature data", 1)],
                [v2],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=_DummyEmbeddingModel(dim))

            results = searcher.search("data", top_k=5, score_threshold=0.0)
            assert len(results) == 2

            ctx = searcher.retrieve_context(
                "data", top_k=5, score_threshold=0.0, metadata_filter={"category": "risk"}
            )
            assert ctx.total_results == 1
            assert ctx.filtered_by_metadata is True

    def test_score_threshold(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            dim = 384
            store = FAISSStore(
                index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim
            )
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "general", "data", 1)],
                [_get_dummy_embedding("data", dim)],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=_DummyEmbeddingModel(dim))

            high_thresh = searcher.search("unrelated", top_k=5, score_threshold=0.99)
            assert len(high_thresh) == 0

            low_thresh = searcher.search("unrelated", top_k=5, score_threshold=0.0)
            assert len(low_thresh) >= 1


class TestContextBuilder:
    def test_build_llm_context_empty(self):
        from knowledge.models import RetrievalContext
        from knowledge.retriever import ContextBuilder

        ctx = RetrievalContext("test", [], "", total_results=0)
        result = ContextBuilder.build_llm_context(ctx)
        assert "Found 0 relevant passages" in result

    def test_build_llm_context_with_results(self):
        from knowledge.models import RetrievalContext, SearchResult
        from knowledge.retriever import ContextBuilder

        r = SearchResult("c1", "d1", "Title", "src", "cat", "Content text", 0.95, 1)
        ctx = RetrievalContext("query", [r], "Content text", total_results=1)
        result = ContextBuilder.build_llm_context(ctx)
        assert "Title" in result
        assert "Content text" in result

    def test_build_sectioned_context(self):
        from knowledge.models import RetrievalContext, SearchResult
        from knowledge.retriever import ContextBuilder

        r = SearchResult("c1", "d1", "T", "s", "reports", "txt", 0.9, 1)
        ctx = RetrievalContext("q", [r], "txt", total_results=1)
        sections = ContextBuilder.build_sectioned_context(ctx)
        assert "reports" in sections

    def test_format_for_dashboard(self):
        from knowledge.models import RetrievalContext, SearchResult
        from knowledge.retriever import ContextBuilder

        r = SearchResult("c1", "d1", "T", "s", "cat", "txt", 0.9, 1)
        ctx = RetrievalContext("q", [r], "txt", total_results=1, latency_ms=12.5)
        formatted = ContextBuilder.format_for_dashboard(ctx)
        assert formatted["query"] == "q"
        assert formatted["latency_ms"] == 12.5
