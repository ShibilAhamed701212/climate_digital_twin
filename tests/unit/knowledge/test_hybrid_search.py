"""Unit tests for HybridSearch."""

from unittest.mock import MagicMock

import pytest

from knowledge.models import SearchResult


def make_result(
    chunk_id="c1",
    doc_id="d1",
    title="Doc",
    source="src",
    category="general",
    content="text",
    score=0.5,
    chunk_number=1,
    page_number=0,
    date="",
    region="",
    keywords=None,
):
    return SearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        title=title,
        source=source,
        category=category,
        content=content,
        score=score,
        chunk_number=chunk_number,
        page_number=page_number,
        date=date,
        region=region,
        keywords=keywords or [],
    )


class TestHybridSearch:
    def _make_search(self):
        from knowledge.retriever.hybrid_search import HybridSearch

        vector_store = MagicMock()
        embedding_model = MagicMock()
        embedding_model.embed_query.return_value = [0.1] * 384
        vector_store.search.return_value = []
        return HybridSearch(vector_store, embedding_model), vector_store, embedding_model

    def test_dense_search(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1, 0.2, 0.3]
        vs.search.return_value = [make_result("c1", score=0.9)]
        results = hs.dense_search("test query", k=5)
        em.embed_query.assert_called_once_with("test query")
        vs.search.assert_called_once()
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_sparse_search_empty_index(self):
        hs, vs, em = self._make_search()
        results = hs.sparse_search("test query", k=5)
        assert results == []

    def test_sparse_search_with_bm25_index(self):
        hs, vs, em = self._make_search()
        hs.build_bm25_index(["c1", "c2"], ["rainfall in karnataka", "temperature data"])
        vs.get_chunk_text.side_effect = lambda cid: {
            "c1": "rainfall in karnataka",
            "c2": "temperature data",
        }.get(cid, "")
        vs.get_chunk_metadata.return_value = {}
        vs.list_sources.return_value = []
        results = hs.sparse_search("rainfall", k=5)
        assert len(results) > 0
        assert any("rainfall" in r.content for r in results)

    def test_sparse_search_no_match(self):
        hs, vs, em = self._make_search()
        hs.build_bm25_index(["c1"], ["rainfall in karnataka"])
        results = hs.sparse_search("zzzzznotfound", k=5)
        assert results == []

    def test_sparse_search_empty_query_terms(self):
        hs, vs, em = self._make_search()
        hs.build_bm25_index(["c1"], ["rainfall data"])
        results = hs.sparse_search("the a an", k=5)
        assert results == []

    def test_hybrid_search_only_dense(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1] * 3
        vs.search.return_value = [make_result("c1", score=0.8)]
        results = hs.hybrid_search("test", k=5)
        assert len(results) >= 1

    def test_hybrid_search_only_sparse(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1] * 3
        vs.search.return_value = []
        hs.build_bm25_index(["c1"], ["rainfall data"])
        vs.get_chunk_text.return_value = "rainfall data"
        vs.get_chunk_metadata.return_value = {}
        vs.list_sources.return_value = []
        results = hs.hybrid_search("rainfall", k=5)
        assert len(results) >= 1

    def test_hybrid_search_both(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1] * 3
        vs.search.return_value = [make_result("c1", score=0.8, content="rainfall in karnataka")]
        hs.build_bm25_index(["c1", "c2"], ["rainfall in karnataka", "temperature data"])
        vs.get_chunk_text.side_effect = lambda cid: {
            "c1": "rainfall in karnataka",
            "c2": "temperature data",
        }.get(cid, "")
        vs.get_chunk_metadata.return_value = {}
        vs.list_sources.return_value = []
        results = hs.hybrid_search("rainfall karnataka", k=5)
        assert results

    def test_rrf_fusion(self):
        hs, vs, em = self._make_search()
        dense = [make_result("c1", score=0.9), make_result("c2", score=0.8)]
        sparse = [make_result("c2"), make_result("c3")]
        fused = hs.rrf_fusion(dense, sparse, k=60)
        assert len(fused) == 3
        cids = [r.chunk_id for r in fused]
        assert "c1" in cids
        assert "c2" in cids
        assert "c3" in cids

    def test_keyword_extract(self):
        hs, vs, em = self._make_search()
        keywords = hs.keyword_extract("The rainfall in Karnataka during monsoon")
        assert "rainfall" in keywords
        assert "karnataka" in keywords
        assert "monsoon" in keywords
        assert "the" not in keywords
        assert "in" not in keywords

    def test_keyword_extract_empty(self):
        hs, vs, em = self._make_search()
        keywords = hs.keyword_extract("a an the")
        assert keywords == []

    def test_build_bm25_index(self):
        hs, vs, em = self._make_search()
        hs.build_bm25_index(["c1", "c2"], ["rainfall data", "temperature data"])
        assert len(hs._bm25_corpus) == 2
        assert hs._bm25_avgdl > 0

    def test_build_bm25_index_empty(self):
        hs, vs, em = self._make_search()
        hs.build_bm25_index([], [])
        assert hs._bm25_corpus == []
        assert hs._bm25_avgdl == 0.0

    def test_fallback_sparse_no_query_terms(self):
        hs, vs, em = self._make_search()
        results = hs._fallback_sparse("a an the", k=5)
        assert results == []

    def test_lookup_metadata(self):
        hs, vs, em = self._make_search()
        vs.get_chunk_text.return_value = "some text"
        vs.get_chunk_metadata.return_value = {"title": "My Doc", "source": "test"}
        meta = hs._lookup_metadata("c1")
        assert meta["title"] == "My Doc"
        assert meta["content"] == "some text"

    def test_lookup_metadata_empty(self):
        hs, vs, em = self._make_search()
        vs.get_chunk_text.return_value = "text"
        vs.get_chunk_metadata.return_value = None
        meta = hs._lookup_metadata("c1")
        assert meta == {"content": "text"}

    def test_bm25_score_no_docs(self):
        hs, vs, em = self._make_search()
        scores = hs._bm25_score(["test"])
        assert scores == {}

    def test_bm25_score_normalization(self):
        hs, vs, em = self._make_search()
        hs._bm25_corpus = [["rainfall", "karnataka"], ["temperature", "data"]]
        hs._bm25_chunk_ids = ["c1", "c2"]
        hs._bm25_avgdl = 2.0
        scores = hs._bm25_score(["rainfall"])
        assert "c1" in scores
        assert 0.0 <= scores["c1"] <= 1.0

    def test_single_result_edge_case(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1] * 3
        vs.search.return_value = [make_result("c1", score=0.5)]
        results = hs.dense_search("query", k=1)
        assert len(results) == 1

    def test_result_deduplication(self):
        hs, vs, em = self._make_search()
        dense = [make_result("c1", score=0.9), make_result("c1", score=0.9)]
        sparse = [make_result("c1")]
        fused = hs.rrf_fusion(dense, sparse, k=60)
        cid_counts = {}
        for r in fused:
            cid_counts[r.chunk_id] = cid_counts.get(r.chunk_id, 0) + 1
        assert cid_counts["c1"] == 1

    def test_dense_search_error_handling(self):
        hs, vs, em = self._make_search()
        em.embed_query.side_effect = RuntimeError("model failed")
        with pytest.raises(RuntimeError):
            hs.dense_search("test")

    def test_hybrid_search_fallback_dense(self):
        hs, vs, em = self._make_search()
        em.embed_query.return_value = [0.1] * 3
        vs.search.return_value = [make_result("c1", score=0.8)]
        results = hs.hybrid_search("test", k=5, _dense_weight=1.0)
        assert len(results) >= 1

    def test_tokenize(self):
        hs, vs, em = self._make_search()
        tokens = hs._tokenize("Rainfall in Karnataka!")
        assert tokens == ["rainfall", "in", "karnataka"]

    def test_empty_corpus_sparse(self):
        hs, vs, em = self._make_search()
        hs._bm25_corpus = []
        hs._bm25_chunk_ids = []
        results = hs.sparse_search("test")
        assert len(results) == 0


class TestHybridSearchIntegration:
    def test_full_hybrid_flow(self):
        from knowledge.retriever.hybrid_search import HybridSearch

        store = MagicMock()
        model = MagicMock()
        model.embed_query.return_value = [0.1] * 4
        store.search.return_value = [make_result("c1", score=0.7)]
        store.get_chunk_text.return_value = "rainfall data in karnataka"
        store.get_chunk_metadata.return_value = {"title": "Doc", "source": "imd"}
        store.list_sources.return_value = []

        hs = HybridSearch(store, model)
        hs.build_bm25_index(["c1"], ["rainfall data in karnataka"])

        results = hs.hybrid_search("rainfall in karnataka", k=5)
        assert len(results) >= 1
