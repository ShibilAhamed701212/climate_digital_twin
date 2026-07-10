"""Unit tests for SemanticSearch."""

from unittest.mock import MagicMock, patch

from knowledge.models import SearchResult


class TestSemanticSearch:
    def _make_result(
        self,
        chunk_id="c1",
        score=0.9,
        title="Doc",
        source="src",
        category="general",
        content="text",
        region="",
    ):
        return SearchResult(
            chunk_id=chunk_id,
            document_id="d1",
            title=title,
            source=source,
            category=category,
            content=content,
            score=score,
            chunk_number=1,
        )

    def test_init_with_vector_store(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        config = {
            "retrieval": {"top_k": 3, "score_threshold": 0.4, "enable_metadata_filtering": False}
        }
        ss = SemanticSearch(vector_store=vs, embedding_model=em, config=config)
        assert ss.top_k == 3
        assert ss.score_threshold == 0.4
        assert ss.enable_metadata_filtering is False
        assert ss.vector_store is vs

    @patch("knowledge.retriever.semantic_search.load_rag_config")
    def test_init_without_vector_store(self, mock_load):
        mock_load.return_value = {
            "retrieval": {"top_k": 5, "score_threshold": 0.5, "enable_metadata_filtering": True},
            "vector_store": {"index_path": "/tmp/i", "metadata_path": "/tmp/m"},
        }
        from knowledge.retriever.semantic_search import SemanticSearch

        em = MagicMock()
        em.dimension = 384
        with patch("knowledge.retriever.semantic_search.FAISSStore") as mock_vs:
            ss = SemanticSearch(embedding_model=em)
            assert ss.vector_store is not None
            mock_vs.assert_called_once()

    def test_search_uses_defaults(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2, 0.3]
        vs.search.return_value = [self._make_result("c1", 0.9)]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={"retrieval": {"top_k": 5, "score_threshold": 0.5}},
        )
        results = ss.search("test query")
        assert len(results) == 1
        em.encode_single.assert_called_once_with("test query")
        vs.search.assert_called_once_with([0.1, 0.2, 0.3], top_k=5)

    def test_search_with_explicit_params(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2]
        vs.search.return_value = [self._make_result("c1", 0.9)]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={"retrieval": {"top_k": 5, "score_threshold": 0.5}},
        )
        results = ss.search("test", top_k=10, score_threshold=0.8)
        vs.search.assert_called_once_with([0.1, 0.2], top_k=10)
        assert len(results) == 1

    def test_search_filters_by_threshold(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2]
        vs.search.return_value = [self._make_result("c1", 0.9), self._make_result("c2", 0.3)]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={"retrieval": {"top_k": 5, "score_threshold": 0.5}},
        )
        results = ss.search("test")
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_retrieve_context(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2]
        vs.search.return_value = [self._make_result("c1", 0.9)]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={"retrieval": {"top_k": 5, "score_threshold": 0.0}},
        )
        ctx = ss.retrieve_context("test query")
        assert ctx.query == "test query"
        assert len(ctx.results) == 1
        assert ctx.total_results == 1
        assert ctx.filtered_by_metadata is False
        assert ctx.latency_ms >= 0
        assert "[1]" in ctx.context_text

    def test_retrieve_context_with_metadata_filter(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2]
        vs.search.return_value = [
            self._make_result("c1", 0.9, category="risk"),
            self._make_result("c2", 0.8, category="climate"),
        ]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True}
            },
        )
        ctx = ss.retrieve_context("test", metadata_filter={"category": "risk"})
        assert len(ctx.results) == 1
        assert ctx.results[0].category == "risk"
        assert ctx.filtered_by_metadata is True

    def test_retrieve_context_no_metadata_filter(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        vs = MagicMock()
        em = MagicMock()
        em.encode_single.return_value = [0.1, 0.2]
        vs.search.return_value = [self._make_result("c1", 0.9)]
        ss = SemanticSearch(
            vector_store=vs,
            embedding_model=em,
            config={
                "retrieval": {
                    "top_k": 5,
                    "score_threshold": 0.0,
                    "enable_metadata_filtering": False,
                }
            },
        )
        ctx = ss.retrieve_context("test", metadata_filter={"category": "risk"})
        assert ctx.filtered_by_metadata is False

    def test_apply_metadata_filter(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        ss = SemanticSearch.__new__(SemanticSearch)
        results = [
            self._make_result("c1", category="risk", region="KA"),
            self._make_result("c2", category="climate", region="TN"),
            self._make_result("c3", category="risk", region="TN"),
        ]
        filtered = ss._apply_metadata_filter(results, {"category": "risk"})
        assert len(filtered) == 2

    def test_apply_metadata_filter_none_value(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        ss = SemanticSearch.__new__(SemanticSearch)
        results = [self._make_result("c1", category="risk")]
        filtered = ss._apply_metadata_filter(results, {"category": None})
        assert len(filtered) == 1

    def test_apply_metadata_filter_case_insensitive(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        ss = SemanticSearch.__new__(SemanticSearch)
        results = [self._make_result("c1", category="Risk")]
        filtered = ss._apply_metadata_filter(results, {"category": "RISK"})
        assert len(filtered) == 1

    def test_build_context_text(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        ss = SemanticSearch.__new__(SemanticSearch)
        results = [self._make_result("c1", 0.95, title="My Doc")]
        ctx = ss._build_context_text(results)
        assert "[1]" in ctx
        assert "My Doc" in ctx
        assert "0.950" in ctx
        assert "---" in ctx

    def test_build_context_text_empty(self):
        from knowledge.retriever.semantic_search import SemanticSearch

        ss = SemanticSearch.__new__(SemanticSearch)
        assert ss._build_context_text([]) == ""
