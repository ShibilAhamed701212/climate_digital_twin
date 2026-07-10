"""Unit tests for KnowledgeAPI."""

import logging
import os
import tempfile

import pytest

logger = logging.getLogger(__name__)

_REAL_EMBEDDINGS: bool | None = None


def real_embeddings_available() -> bool:
    """Check once if the embedding model can fully load (not just package import)."""
    global _REAL_EMBEDDINGS
    if _REAL_EMBEDDINGS is not None:
        return _REAL_EMBEDDINGS
    try:
        from knowledge.embeddings.embedding_model import EmbeddingModel

        m = EmbeddingModel(model_name="all-MiniLM-L6-v2", dimension=384)
        _REAL_EMBEDDINGS = m.is_available()
    except Exception:
        _REAL_EMBEDDINGS = False
    return _REAL_EMBEDDINGS


def _make_cfg(tmp: str) -> dict:
    return {
        "rag": {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
        },
        "retrieval": {
            "top_k": 5,
            "score_threshold": 0.0,
            "enable_metadata_filtering": True,
        },
        "vector_store": {
            "type": "faiss",
            "index_path": f"{tmp}/index.faiss",
            "metadata_path": f"{tmp}/meta.pkl",
        },
        "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
        "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
    }


class TestKnowledgeAPI:
    """Integration tests for KnowledgeAPI (requires real embeddings)."""

    @classmethod
    def setup_class(cls):
        if not real_embeddings_available():
            pytest.skip("Real embedding model unavailable (torch DLL issue) — skipping RAG tests")

    def test_api_initializes(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            assert api.config is not None

    def test_index_and_search(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "test.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Climate Data\n\n"
                    "Rainfall patterns in Karnataka show significant variation across districts.\n"
                    "Coastal regions receive heavy monsoon rainfall from June to September.\n"
                    "Interior districts like Kalaburagi and Vijayapura receive moderate rainfall.\n"
                )
            result = api.index_document(md_path, source="imd", category="climate")
            assert result.success, f"indexing failed: {result.error}"
            assert result.num_chunks >= 1

            results = api.search("rainfall Karnataka monsoon")
            assert len(results) >= 1
            assert results[0].score >= 0.0

    def test_delete_document(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Climate Report\n\n"
                    "Annual rainfall in Karnataka varies across coastal and interior regions.\n"
                    "Monsoon patterns affect agriculture yields in the region.\n"
                )
            result = api.index_document(md_path)
            assert result.success
            removed = api.delete_document(result.document_id)
            assert removed > 0

    def test_list_sources(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Data Sources\n\n"
                    "IMD provides weather station data across Karnataka.\n"
                    "ISRO satellite products offer remote sensing observations.\n"
                )
            api.index_document(md_path)
            sources = api.list_sources()
            assert len(sources) >= 1

    def test_get_index_stats(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Index Stats\n\n"
                    "This document contains information about climate trends.\n"
                    "Multiple data sources are available for analysis.\n"
                )
            api.index_document(md_path)
            stats = api.get_index_stats()
            assert stats["total_documents"] >= 1
            assert stats["total_chunks"] >= 1

    def test_retrieve_context(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Monsoon Season\n\n"
                    "The southwest monsoon arrives in Karnataka in June.\n"
                    "Rainfall patterns determine agricultural planning.\n"
                )
            api.index_document(md_path)
            ctx = api.retrieve_context("monsoon Karnataka rainfall")
            assert ctx.total_results >= 1
            assert ctx.context_text != ""

    def test_rebuild_index(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            api.rebuild_index()
            stats = api.get_index_stats()
            assert stats["total_documents"] == 0

    def test_semantic_search_alias(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            api = KnowledgeAPI(config=_make_cfg(tmp))
            md_path = os.path.join(tmp, "d.md")
            with open(md_path, "w") as f:
                f.write(
                    "# Search Test\n\n"
                    "This document contains text about Karnataka weather patterns.\n"
                    "Search functionality should find relevant content.\n"
                )
            api.index_document(md_path)
            r1 = api.search("Karnataka weather")
            r2 = api.semantic_search("Karnataka weather")
            assert len(r1) == len(r2)
