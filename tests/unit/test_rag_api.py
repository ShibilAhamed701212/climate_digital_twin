"""Unit tests for KnowledgeAPI."""

import os
import tempfile


class TestKnowledgeAPI:
    def test_api_initializes(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            assert api.config is not None

    def test_index_and_search(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)

            md_path = os.path.join(tmp, "test.md")
            with open(md_path, "w") as f:
                f.write("# Climate Data\n\nRainfall patterns in Karnataka.\n")

            result = api.index_document(md_path, source="imd", category="climate")
            assert result.success

            results = api.search("rainfall")
            assert len(results) >= 1
            assert results[0].score >= 0.0

    def test_delete_document(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write("# Doc\n\nContent.\n")
            result = api.index_document(md_path)
            assert result.success

            removed = api.delete_document(result.document_id)
            assert removed > 0

    def test_list_sources(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write("# Doc\n\nText.\n")
            api.index_document(md_path)
            sources = api.list_sources()
            assert len(sources) >= 1

    def test_get_index_stats(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write("# Doc\n\nText.\n")
            api.index_document(md_path)
            stats = api.get_index_stats()
            assert stats["total_documents"] >= 1
            assert stats["total_chunks"] >= 1

    def test_retrieve_context(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            md_path = os.path.join(tmp, "doc.md")
            with open(md_path, "w") as f:
                f.write("# Monsoon\n\nThe southwest monsoon arrives in June.\n")
            api.index_document(md_path)

            ctx = api.retrieve_context("monsoon")
            assert ctx.total_results >= 1
            assert ctx.context_text != ""

    def test_rebuild_index(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            api.rebuild_index()
            stats = api.get_index_stats()
            assert stats["total_documents"] == 0

    def test_semantic_search_alias(self):
        from knowledge.api import KnowledgeAPI

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            api = KnowledgeAPI(config=cfg)
            md_path = os.path.join(tmp, "d.md")
            with open(md_path, "w") as f:
                f.write("# T\n\nC.\n")
            api.index_document(md_path)
            r1 = api.search("test")
            r2 = api.semantic_search("test")
            assert len(r1) == len(r2)
