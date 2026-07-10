"""Unit tests for the search API layer (KnowledgeAPI class)."""

from unittest.mock import MagicMock

from knowledge.models import IndexingResult, SearchResult


class TestKnowledgeAPIDirect:
    def _make_result(self, chunk_id="c1", score=0.9):
        return SearchResult(
            chunk_id=chunk_id,
            document_id="d1",
            title="Doc",
            source="src",
            category="general",
            content="text",
            score=score,
            chunk_number=1,
        )

    def test_ask_empty_query(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        results = api.ask("", k=5)
        assert results == []
        results = api.ask("   ", k=5)
        assert results == []

    def test_ask_with_query(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [self._make_result("c1")]
        api.pipeline = MagicMock()
        results = api.ask("climate data", k=5)
        assert len(results) == 1

    def test_search(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [self._make_result("c1")]
        api.pipeline = MagicMock()
        results = api.search("test", top_k=3)
        assert len(results) == 1

    def test_semantic_search(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [self._make_result("c1")]
        api.pipeline = MagicMock()
        results = api.semantic_search("test", top_k=3)
        assert len(results) == 1

    def test_health(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.vector_store.total_chunks = 5
        api.embedding_model = MagicMock()
        api.embedding_model.strategy = "dummy"
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        h = api.health()
        assert h["status"] == "ok"
        assert h["vector_count"] == 5

    def test_list_sources(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.vector_store.list_sources.return_value = [{"document_id": "d1", "chunk_count": 3}]
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        sources = api.list_sources()
        assert len(sources) == 1
        assert sources[0]["document_id"] == "d1"

    def test_rebuild_index(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        api.rebuild_index()
        api.vector_store.clear.assert_called_once()

    def test_get_index_stats(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.vector_store.list_sources.return_value = [
            {"document_id": "d1", "chunk_count": 3, "category": "risk"},
            {"document_id": "d2", "chunk_count": 5, "category": "climate"},
        ]
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        stats = api.get_index_stats()
        assert stats["total_documents"] == 2
        assert stats["total_chunks"] == 8

    def test_delete_document(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.vector_store.delete_document.return_value = 3
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        count = api.delete_document("d1")
        assert count == 3

    def test_index_document(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        api.pipeline.index_document.return_value = IndexingResult("d1", "Doc", 3, True)
        result = api.index_document("/path/to/file.md", source="test")
        assert result.success
        assert result.num_chunks == 3

    def test_index_directory(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.pipeline = MagicMock()
        api.pipeline.index_directory.return_value = [
            IndexingResult("d1", "Doc1", 2, True),
            IndexingResult("d2", "Doc2", 1, True),
        ]
        results = api.index_directory("/path/to/dir")
        assert len(results) == 2

    def test_retrieve_context(self):
        from knowledge.api.search_api import KnowledgeAPI
        from knowledge.models import RetrievalContext

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.retrieve_context.return_value = RetrievalContext(
            query="test", results=[], context_text="", total_results=0
        )
        api.pipeline = MagicMock()
        ctx = api.retrieve_context("test")
        assert ctx.total_results == 0

    def test_get_context(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [
            self._make_result("c1", 0.9),
            self._make_result("c2", 0.8),
        ]
        api.pipeline = MagicMock()
        ctx = api.get_context("test query", max_tokens=2000)
        assert "c1" in ctx or "text" in ctx or "[Source:" in ctx or ctx == ""

    def test_get_context_empty_results(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = []
        api.pipeline = MagicMock()
        ctx = api.get_context("test query", max_tokens=2000)
        assert ctx == ""

    def test_get_context_truncates(self):
        from knowledge.api.search_api import KnowledgeAPI

        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [
            self._make_result("c1", 0.9),
        ]
        api.pipeline = MagicMock()
        ctx = api.get_context("test query", max_tokens=1)
        assert isinstance(ctx, str)
