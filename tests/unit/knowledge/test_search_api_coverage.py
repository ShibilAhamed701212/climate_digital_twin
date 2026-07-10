"""Additional tests for KnowledgeAPI uncovered lines.

Extends test_search_api.py with tests covering:
- __init__ with config provided
- get_context with empty chunk content (line 111)
- get_context truncation with remaining > 100 (lines 121-122)
"""

from unittest.mock import MagicMock, patch

from knowledge.api.search_api import KnowledgeAPI
from knowledge.models import SearchResult


class TestKnowledgeAPIExtended:
    def _make_result(self, chunk_id="c1", score=0.9, content="text"):
        return SearchResult(
            chunk_id=chunk_id,
            document_id="d1",
            title="Doc",
            source="src",
            category="general",
            content=content,
            score=score,
            chunk_number=1,
        )

    @patch("knowledge.api.search_api.load_rag_config")
    @patch("knowledge.api.search_api.FAISSStore")
    @patch("knowledge.api.search_api.EmbeddingModel")
    @patch("knowledge.api.search_api.IndexingPipeline")
    @patch("knowledge.api.search_api.SemanticSearch")
    def test_init_with_config(self, mock_ss, mock_pipe, mock_em, mock_vs, mock_load):
        config = {
            "rag": {"embedding_dimension": 128},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
        }
        api = KnowledgeAPI(config=config)
        assert api.config is config

    def test_get_context_skips_empty_content(self):
        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        api.searcher.search.return_value = [
            self._make_result("c1", 0.9, content=""),
            self._make_result("c2", 0.8, content="real content"),
        ]
        api.pipeline = MagicMock()
        ctx = api.get_context("test query")
        assert "real content" in ctx

    def test_get_context_truncates_with_remaining(self):
        api = KnowledgeAPI.__new__(KnowledgeAPI)
        api.config = {"rag": {}, "retrieval": {}, "vector_store": {}}
        api.vector_store = MagicMock()
        api.embedding_model = MagicMock()
        api.searcher = MagicMock()
        long_content = "A" * 500
        api.searcher.search.return_value = [
            self._make_result("c1", 0.9, content=long_content),
        ]
        api.pipeline = MagicMock()
        ctx = api.get_context("test query", max_tokens=10)
        assert isinstance(ctx, str)
        assert len(ctx) < len(long_content)
