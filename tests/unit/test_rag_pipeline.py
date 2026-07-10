"""Unit tests for the indexing pipeline."""

import os
import tempfile

import pytest


def _real_embeddings_available() -> bool:
    try:
        from knowledge.embeddings.embedding_model import EmbeddingModel

        m = EmbeddingModel(model_name="all-MiniLM-L6-v2", dimension=384)
        return m.is_available()
    except Exception:
        return False


class TestIndexingPipeline:
    @classmethod
    def setup_class(cls):
        if not _real_embeddings_available():
            pytest.skip("Real embedding model unavailable (torch DLL) — skipping pipeline tests")

    def test_index_markdown_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
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
            md_path = os.path.join(tmp, "test.md")
            text = "# Test Doc\n\nContent here.\n\nMore content on second paragraph.\n"
            with open(md_path, "w") as f:
                f.write(text)

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(md_path, source="test")
            assert result.success
            assert result.num_chunks >= 1

    def test_index_text_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
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
            txt_path = os.path.join(tmp, "notes.txt")
            text = "Simple text document for testing climate rainfall temperature and humidity patterns."
            with open(txt_path, "w") as f:
                f.write(text)

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(txt_path)
            assert result.success
            assert result.num_chunks == 1

    def test_index_unsupported_format(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
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
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            csv_path = os.path.join(tmp, "data.csv")
            with open(csv_path, "w") as f:
                f.write("a,b,c\n1,2,3\n")

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(csv_path)
            assert not result.success

    def test_index_empty_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
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
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            empty_path = os.path.join(tmp, "empty.txt")
            with open(empty_path, "w") as f:
                f.write("")

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(empty_path)
            assert not result.success

    def test_index_directory(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
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
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            for fname, content in [
                (
                    "a.md",
                    "# Section A\n\nContent about climate rainfall temperature and humidity patterns.",
                ),
                ("b.txt", "Simple notes about weather forecasting and climate science."),
                ("c.csv", "x,y\n1,2\n3,4\n"),
            ]:
                with open(os.path.join(tmp, fname), "w") as f:
                    f.write(content)

            pipeline = IndexingPipeline(config=cfg)
            results = pipeline.index_directory(tmp)
            assert all(r.success for r in results)
