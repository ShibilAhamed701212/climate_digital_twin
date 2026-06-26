"""Unit tests for RAG config loader."""

import os
import tempfile

import yaml


class TestConfigLoader:
    def test_load_defaults(self):
        from knowledge.config_loader import load_rag_config

        cfg = load_rag_config("/nonexistent/path.yaml")
        assert cfg["rag"]["chunk_size"] == 700
        assert cfg["rag"]["chunk_overlap"] == 120
        assert cfg["rag"]["embedding_model"] == "all-MiniLM-L6-v2"
        assert cfg["retrieval"]["top_k"] == 5
        assert cfg["vector_store"]["type"] == "faiss"

    def test_load_custom_config(self):
        from knowledge.config_loader import load_rag_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"rag": {"chunk_size": 300, "chunk_overlap": 50}}, f)
            f.flush()
            path = f.name
        try:
            cfg = load_rag_config(path)
            assert cfg["rag"]["chunk_size"] == 300
            assert cfg["rag"]["chunk_overlap"] == 50
        finally:
            os.unlink(path)

    def test_load_partial_config(self):
        from knowledge.config_loader import load_rag_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"retrieval": {"top_k": 10}}, f)
            f.flush()
            path = f.name
        try:
            cfg = load_rag_config(path)
            assert cfg["retrieval"]["top_k"] == 10
            assert cfg["rag"]["chunk_size"] == 700
        finally:
            os.unlink(path)
