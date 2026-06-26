"""Unit tests for the indexing pipeline."""

import os
import tempfile


class TestIndexingPipeline:
    def test_index_markdown_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            md_path = os.path.join(tmp, "test.md")
            with open(md_path, "w") as f:
                f.write("# Test Doc\n\nContent here.\n\nMore content on second paragraph.\n")

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(md_path, source="test")
            assert result.success
            assert result.num_chunks >= 1

    def test_index_text_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            txt_path = os.path.join(tmp, "notes.txt")
            with open(txt_path, "w") as f:
                f.write("Simple text document for testing.")

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(txt_path)
            assert result.success
            assert result.num_chunks == 1

    def test_index_unsupported_format(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            csv_path = os.path.join(tmp, "data.csv")
            with open(csv_path, "w") as f:
                f.write("a,b\n1,2\n")

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document(csv_path)
            assert not result.success
            assert "not in supported list" in result.error

    def test_index_nonexistent_file(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384}, "retrieval": {"top_k": 5, "score_threshold": 0.0}, "vector_store": {"type": "faiss", "index_path": f"{tmp}/idx.faiss", "metadata_path": f"{tmp}/meta.pkl"}, "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]}, "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"}}

            pipeline = IndexingPipeline(config=cfg)
            result = pipeline.index_document("/nonexistent/file.md")
            assert not result.success

    def test_index_directory(self):
        from knowledge.pipelines import IndexingPipeline

        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "rag": {"chunk_size": 500, "chunk_overlap": 50, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
                "retrieval": {"top_k": 5, "score_threshold": 0.0, "enable_metadata_filtering": True},
                "vector_store": {"type": "faiss", "index_path": f"{tmp}/index.faiss", "metadata_path": f"{tmp}/meta.pkl"},
                "documents": {"base_path": tmp, "supported_formats": ["md", "txt", "csv", "json"]},
                "logging": {"log_path": f"{tmp}/rag.log", "log_level": "INFO"},
            }
            for fname in ["a.md", "b.txt", "c.csv"]:
                with open(os.path.join(tmp, fname), "w") as f:
                    if fname.endswith(".csv"):
                        f.write("name,value\nrainfall,120\n")
                    else:
                        f.write(f"Content of {fname} with enough text so that it is longer.")

            pipeline = IndexingPipeline(config=cfg)
            results = pipeline.index_directory(tmp, recursive=False)
            assert len(results) == 3
            assert all(r.success for r in results)
