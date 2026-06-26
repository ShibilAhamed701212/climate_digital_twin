"""Unit tests for FAISS vector store."""

import tempfile

import pytest


class TestFAISSStore:
    def test_add_and_search(self):
        from knowledge.models import Chunk
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/index.faiss",
                metadata_path=f"{tmp}/meta.pkl",
                dimension=4,
            )
            chunks = [
                Chunk("c1", "d1", "Doc A", "src", "general", "rainfall data", 1),
                Chunk("c2", "d2", "Doc B", "src", "general", "temperature data", 1),
            ]
            embeddings = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
            store.add(chunks, embeddings)
            assert store.total_chunks == 2

            query = [1.0, 0.0, 0.0, 0.0]
            results = store.search(query, top_k=2)
            assert len(results) == 2
            assert results[0].score >= results[1].score
            assert results[0].content == "rainfall data"

    def test_search_empty_index(self):
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/empty.faiss",
                metadata_path=f"{tmp}/empty.pkl",
                dimension=4,
            )
            results = store.search([1.0, 0.0, 0.0, 0.0], top_k=5)
            assert results == []

    def test_delete_document(self):
        from knowledge.models import Chunk
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/index.faiss",
                metadata_path=f"{tmp}/meta.pkl",
                dimension=2,
            )
            chunks = [
                Chunk("c1", "d1", "Doc A", "src", "general", "text a", 1),
                Chunk("c2", "d2", "Doc B", "src", "general", "text b", 1),
            ]
            embeddings = [[1.0, 0.0], [0.0, 1.0]]
            store.add(chunks, embeddings)
            assert store.total_chunks == 2

            removed = store.delete_document("d1")
            assert removed == 1
            assert store.total_chunks == 1

    def test_clear(self):
        from knowledge.models import Chunk
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/index.faiss",
                metadata_path=f"{tmp}/meta.pkl",
                dimension=2,
            )
            store.add(
                [Chunk("c1", "d1", "T", "s", "g", "txt", 1)],
                [[1.0, 0.0]],
            )
            assert store.total_chunks == 1
            store.clear()
            assert store.total_chunks == 0

    def test_list_sources(self):
        from knowledge.models import Chunk
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/index.faiss",
                metadata_path=f"{tmp}/meta.pkl",
                dimension=2,
            )
            store.add(
                [Chunk("c1", "d1", "Doc One", "src", "reports", "txt", 1)],
                [[1.0, 0.0]],
            )
            sources = store.list_sources()
            assert len(sources) == 1
            assert sources[0]["document_id"] == "d1"
            assert sources[0]["chunk_count"] == 1

    def test_mismatched_inputs_raises(self):
        from knowledge.models import Chunk
        from knowledge.vector_store import FAISSStore

        with tempfile.TemporaryDirectory() as tmp:
            store = FAISSStore(
                index_path=f"{tmp}/index.faiss",
                metadata_path=f"{tmp}/meta.pkl",
                dimension=2,
            )
            with pytest.raises(ValueError):
                store.add(
                    [Chunk("c1", "d1", "T", "s", "g", "txt", 1)],
                    [[1.0, 0.0], [0.0, 1.0]],
                )
