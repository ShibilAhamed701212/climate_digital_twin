"""Unit tests for semantic search and context builder."""

import tempfile


class TestSemanticSearch:
    def _make_store(self, tmp: str, dim: int = 384) -> tuple:
        from knowledge.vector_store import FAISSStore
        return FAISSStore(
            index_path=f"{tmp}/index.faiss",
            metadata_path=f"{tmp}/meta.pkl",
            dimension=dim,
        )

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
        from knowledge.embeddings import EmbeddingModel
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            emb = EmbeddingModel()
            dim = emb.dimension
            store = FAISSStore(index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim)
            emb_vec = emb.encode_single("rainfall data")
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "general", "rainfall data", 1)],
                [emb_vec],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=emb)
            ctx = searcher.retrieve_context("rainfall", top_k=5)
            assert ctx.total_results == 1

    def test_metadata_filter(self):
        from knowledge.embeddings import EmbeddingModel
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            emb = EmbeddingModel()
            dim = emb.dimension
            store = FAISSStore(index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim)
            v1 = emb.encode_single("flood risk data")
            v2 = emb.encode_single("temperature data")
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "risk", "flood risk data", 1)],
                [v1],
            )
            store.add(
                [Chunk("c2", "d2", "Doc2", "src", "general", "temperature data", 1)],
                [v2],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=emb)

            results = searcher.search("data", top_k=5)
            assert len(results) == 2

            ctx = searcher.retrieve_context("data", top_k=5, metadata_filter={"category": "risk"})
            assert ctx.total_results == 1
            assert ctx.filtered_by_metadata is True

    def test_score_threshold(self):
        from knowledge.embeddings import EmbeddingModel
        from knowledge.models import Chunk
        from knowledge.retriever import SemanticSearch
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            emb = EmbeddingModel()
            dim = emb.dimension
            store = FAISSStore(index_path=f"{tmp}/idx.faiss", metadata_path=f"{tmp}/meta.pkl", dimension=dim)
            store.add(
                [Chunk("c1", "d1", "Doc", "src", "general", "data", 1)],
                [emb.encode_single("data")],
            )
            searcher = SemanticSearch(vector_store=store, embedding_model=emb)

            high_thresh = searcher.search("unrelated", top_k=5, score_threshold=0.99)
            assert len(high_thresh) == 0

            low_thresh = searcher.search("unrelated", top_k=5, score_threshold=0.0)
            assert len(low_thresh) == 1


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
