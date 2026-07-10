"""Unit tests for FAISSStore and DebouncedSaver."""

import json
import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from knowledge.models import Chunk
from knowledge.vector_store.faiss_store import DebouncedSaver, FAISSStore


class TestDebouncedSaver:
    def test_save_called(self):
        func = MagicMock()
        ds = DebouncedSaver(func, delay=0.01)
        ds._save()
        func.assert_called_once()

    def test_flush_cancels_timer_and_saves(self):
        func = MagicMock()
        ds = DebouncedSaver(func, delay=10.0)
        ds._timer = threading.Timer(10.0, ds._save)
        ds._timer.start()
        ds.flush()
        func.assert_called_once()
        assert ds._timer is None

    def test_schedule_cancels_existing_timer(self):
        func = MagicMock()
        ds = DebouncedSaver(func, delay=10.0)
        old_timer = threading.Timer(10.0, ds._save)
        ds._timer = old_timer
        ds.schedule()
        assert ds._timer is not old_timer


class TestFAISSStoreBuildIndex:
    def _make_store(self):
        store = FAISSStore.__new__(FAISSStore)
        store.dimension = 384
        store._index_type = "flat"
        return store

    def test_build_faiss_flat(self):
        import faiss

        store = self._make_store()
        store._index_type = "flat"
        idx = store._build_faiss_index()
        assert isinstance(idx, faiss.IndexIDMap)

    def test_build_faiss_ivf(self):
        import faiss

        store = self._make_store()
        store._index_type = "ivf"
        idx = store._build_faiss_index()
        assert isinstance(idx, faiss.IndexIDMap)

    def test_build_faiss_hnsw(self):
        import faiss

        store = self._make_store()
        store._index_type = "hnsw"
        idx = store._build_faiss_index()
        assert isinstance(idx, faiss.IndexIDMap)

    def test_build_faiss_unknown_type(self):
        store = self._make_store()
        store._index_type = "unknown"
        with pytest.raises(ValueError, match="Unknown index_type"):
            store._build_faiss_index()


class TestFAISSStoreLoad:
    def test_load_index_existing_file(self, tmp_path):
        import faiss

        index_path = str(tmp_path / "index.faiss")
        idx = faiss.IndexIDMap(faiss.IndexFlatIP(384))
        faiss.write_index(idx, index_path)

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = index_path
        store.metadata_path = str(tmp_path / "meta.json")
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = None
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        store._load_index()
        assert store._index is not None
        assert store._index.ntotal == 0

    def test_load_index_creates_new_when_no_file(self, tmp_path):
        store = FAISSStore.__new__(FAISSStore)
        store.index_path = str(tmp_path / "nonexistent.faiss")
        store.metadata_path = str(tmp_path / "meta.json")
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = None
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        store._load_index()
        assert store._index is not None

    def test_load_index_faiss_unavailable(self, tmp_path):
        import faiss

        index_path = str(tmp_path / "index.faiss")
        Path(index_path).write_text("garbage")

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = index_path
        store.metadata_path = str(tmp_path / "meta.json")
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = None
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        with patch.object(faiss, "read_index", side_effect=Exception("not avail")):
            store._load_index()
        assert store._index is None

    def test_load_metadata(self, tmp_path):
        import faiss

        meta_path = str(tmp_path / "meta.json")
        data = {
            "id_to_idx": {"c1": 0},
            "idx_to_id": {"0": "c1"},
            "metadatas": {"c1": {"doc_id": "d1"}},
            "chunk_texts": {"c1": "hello"},
            "next_idx": 1,
        }
        with open(meta_path, "w") as f:
            json.dump(data, f)

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = str(tmp_path / "nonexistent.faiss")
        store.metadata_path = meta_path
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = None
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        with patch.object(faiss, "read_index", side_effect=Exception("not avail")):
            store._load_index()
        assert store._id_to_idx == {"c1": 0}
        assert store._idx_to_id == {0: "c1"}
        assert store._metadatas == {"c1": {"doc_id": "d1"}}
        assert store._chunk_texts == {"c1": "hello"}
        assert store._next_idx == 1

    def test_load_metadata_corrupt(self, tmp_path):
        import faiss

        meta_path = str(tmp_path / "meta.json")
        with open(meta_path, "w") as f:
            f.write("not json")

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = str(tmp_path / "nonexistent.faiss")
        store.metadata_path = meta_path
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = None
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        with patch.object(faiss, "read_index", side_effect=Exception("not avail")):
            store._load_index()
        assert store._metadatas == {}

    def test_save_index(self, tmp_path):
        import faiss

        index_path = str(tmp_path / "save_test.faiss")
        store = FAISSStore.__new__(FAISSStore)
        store.index_path = index_path
        store.metadata_path = str(tmp_path / "meta.json")
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = faiss.IndexIDMap(faiss.IndexFlatIP(384))
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        store._save_index()
        assert os.path.exists(index_path)

    def test_save_index_exception(self):
        import faiss

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = "/nonexistent/dir/index.faiss"
        store.metadata_path = "/nonexistent/meta.json"
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = MagicMock()
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        with patch.object(faiss, "write_index", side_effect=Exception("write fail")):
            store._save_index()

    def test_save_metadata(self, tmp_path):
        meta_path = str(tmp_path / "meta.json")
        store = FAISSStore.__new__(FAISSStore)
        store.index_path = str(tmp_path / "idx.faiss")
        store.metadata_path = meta_path
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = MagicMock()
        store._id_to_idx = {"c1": 0}
        store._idx_to_id = {0: "c1"}
        store._metadatas = {"c1": {"doc_id": "d1"}}
        store._chunk_texts = {"c1": "hello"}
        store._next_idx = 1
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()

        store._save_metadata()
        with open(meta_path) as f:
            saved = json.load(f)
        assert saved["id_to_idx"] == {"c1": 0}
        assert saved["next_idx"] == 1


class TestFAISSStoreOperations:
    def _make_store(self, tmp_path):
        import faiss

        store = FAISSStore.__new__(FAISSStore)
        store.index_path = str(tmp_path / "idx.faiss")
        store.metadata_path = str(tmp_path / "meta.json")
        store.dimension = 384
        store._index_type = "flat"
        store._lock = threading.Lock()
        store._index = faiss.IndexIDMap(faiss.IndexFlatIP(384))
        store._id_to_idx = {}
        store._idx_to_id = {}
        store._metadatas = {}
        store._chunk_texts = {}
        store._next_idx = 0
        store._debounced_index_save = MagicMock()
        store._debounced_metadata_save = MagicMock()
        return store

    def make_chunk(self, cid="c1", content="text"):
        return Chunk(
            chunk_id=cid,
            document_id="d1",
            title="Doc",
            source="src",
            category="general",
            content=content,
            chunk_number=1,
        )

    def test_add_empty_chunks(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add([], [])
        assert store._next_idx == 0

    def test_add_rebuilds_index_when_none(self, tmp_path):
        store = self._make_store(tmp_path)
        store._index = None
        chunks = [self.make_chunk("c1", "hello")]
        emb = [[0.1] * 384]
        store.add(chunks, emb)
        assert store._index is not None
        assert store._index.ntotal == 1

    def test_add_vectors_empty(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add_vectors([], np.array([]))
        assert store._next_idx == 0

    def test_add_vectors_dim_mismatch(self, tmp_path):
        store = self._make_store(tmp_path)
        with pytest.raises(ValueError, match="Embedding dimension"):
            store.add_vectors(["c1"], np.array([[0.1, 0.2]]))

    def test_add_vectors_count_mismatch(self, tmp_path):
        store = self._make_store(tmp_path)
        with pytest.raises(ValueError, match="does not match"):
            store.add_vectors(["c1", "c2"], np.array([[0.1] * 384]))

    def test_add_vectors_with_metadatas_and_texts(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add_vectors(
            chunk_ids=["c1", "c2"],
            embeddings=np.array([[0.1] * 384, [0.2] * 384], dtype=np.float32),
            metadatas=[{"doc": "a"}, {"doc": "b"}],
            texts=["hello", "world"],
        )
        assert store._metadatas["c1"] == {"doc": "a"}
        assert store._chunk_texts["c2"] == "world"
        assert store._next_idx == 2

    def test_add_vectors_without_metadatas(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add_vectors(
            chunk_ids=["c1"],
            embeddings=np.array([[0.1] * 384], dtype=np.float32),
        )
        assert store._metadatas["c1"] == {}

    def test_add_vectors_rebuilds_index(self, tmp_path):
        store = self._make_store(tmp_path)
        store._index = None
        store.add_vectors(
            chunk_ids=["c1"],
            embeddings=np.array([[0.1] * 384], dtype=np.float32),
        )
        assert store._index is not None

    def test_search_empty_index(self, tmp_path):
        store = self._make_store(tmp_path)
        store._index = None
        results = store.search([0.1] * 384)
        assert results == []

    def test_search_returns_results(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [self.make_chunk("c1", "hello world")]
        emb = [[0.1] * 384]
        store.add(chunks, emb)
        results = store.search([0.1] * 384)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_search_skips_negative_idx(self, tmp_path):
        store = self._make_store(tmp_path)
        store._index = MagicMock()
        store._index.ntotal = 5
        store._index.search.return_value = (np.array([[0.5, -1.0]]), np.array([[0, -1]]))
        store._idx_to_id = {0: "c1"}
        store._metadatas = {"c1": {"doc_id": "d1"}}
        store._chunk_texts = {"c1": "text"}
        results = store.search([0.1] * 384)
        assert len(results) == 1

    def test_search_skips_missing_cid(self, tmp_path):
        store = self._make_store(tmp_path)
        store._index = MagicMock()
        store._index.ntotal = 5
        store._index.search.return_value = (np.array([[0.5]]), np.array([[999]]))
        store._idx_to_id = {}
        results = store.search([0.1] * 384)
        assert results == []

    def test_search_metadata_filter(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [
            self.make_chunk("c1", "hello"),
            self.make_chunk("c2", "world"),
        ]
        emb = [[0.1] * 384, [0.2] * 384]
        store.add(chunks, emb)
        store._metadatas["c1"] = {"doc_id": "d1", "region": "Karnataka"}
        store._metadatas["c2"] = {"doc_id": "d1", "region": "Tamil Nadu"}
        results = store.search([0.1] * 384, metadata_filter={"region": "Karnataka"}, top_k=5)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_search_metadata_filter_none_match(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [self.make_chunk("c1", "hello")]
        store.add(chunks, [[0.1] * 384])
        store._metadatas["c1"] = {"doc_id": "d1", "region": "Karnataka"}
        results = store.search([0.1] * 384, metadata_filter={"region": "Kerala"}, top_k=5)
        assert len(results) == 0

    def test_delete_no_chunk_ids(self, tmp_path):
        store = self._make_store(tmp_path)
        store.delete([])
        store._debounced_index_save.schedule.assert_not_called()

    def test_delete_removes_chunks(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [self.make_chunk("c1", "hello")]
        store.add(chunks, [[0.1] * 384])
        store.delete(["c1"])
        assert "c1" not in store._id_to_idx
        assert store._idx_to_id == {}

    def test_build_index_empty_embeddings(self, tmp_path):
        store = self._make_store(tmp_path)
        store.build_index(np.array([]).reshape(0, 384))
        assert store._next_idx == 0

    def test_build_index_with_embeddings(self, tmp_path):
        store = self._make_store(tmp_path)
        embeddings = np.array([[0.1] * 384, [0.2] * 384], dtype=np.float32)
        store.build_index(
            embeddings, chunk_ids=["c1", "c2"], metadatas=[{"a": 1}, {"b": 2}], texts=["t1", "t2"]
        )
        assert store._next_idx == 2
        assert store._metadatas["c1"] == {"a": 1}
        assert store._chunk_texts["c2"] == "t2"

    def test_build_index_without_chunk_ids(self, tmp_path):
        store = self._make_store(tmp_path)
        embeddings = np.array([[0.1] * 384], dtype=np.float32)
        store.build_index(embeddings)
        assert store._next_idx == 1
        cid = list(store._id_to_idx.keys())[0]
        assert cid.startswith("chunk_")

    def test_clear(self, tmp_path):
        store = self._make_store(tmp_path)
        store.add([self.make_chunk("c1")], [[0.1] * 384])
        store.clear()
        assert store._next_idx == 0
        assert store._metadatas == {}

    def test_get_chunk_text(self, tmp_path):
        store = self._make_store(tmp_path)
        store._chunk_texts["c1"] = "hello"
        assert store.get_chunk_text("c1") == "hello"
        assert store.get_chunk_text("nonexistent") == ""

    def test_get_chunk_metadata(self, tmp_path):
        store = self._make_store(tmp_path)
        store._metadatas["c1"] = {"key": "val"}
        assert store.get_chunk_metadata("c1") == {"key": "val"}
        assert store.get_chunk_metadata("nonexistent") == {}

    def test_len(self, tmp_path):
        store = self._make_store(tmp_path)
        store._metadatas["c1"] = {}
        assert len(store) == 1

    def test_contains(self, tmp_path):
        store = self._make_store(tmp_path)
        store._id_to_idx["c1"] = 0
        assert "c1" in store
        assert "c2" not in store

    def test_list_sources(self, tmp_path):
        store = self._make_store(tmp_path)
        store._metadatas = {
            "c1": {"document_id": "d1", "title": "Doc1", "source": "src1", "category": "cat1"},
            "c2": {"document_id": "d1", "title": "Doc1", "source": "src1", "category": "cat1"},
            "c3": {"document_id": "d2", "title": "Doc2", "source": "src2", "category": "cat2"},
        }
        sources = store.list_sources()
        assert len(sources) == 2
        d1 = [s for s in sources if s["document_id"] == "d1"][0]
        assert d1["chunk_count"] == 2

    def test_total_chunks(self, tmp_path):
        store = self._make_store(tmp_path)
        store._metadatas["c1"] = {}
        assert store.total_chunks == 1

    def test_delete_document(self, tmp_path):
        store = self._make_store(tmp_path)
        store._metadatas = {
            "c1": {"document_id": "d1"},
            "c2": {"document_id": "d1"},
            "c3": {"document_id": "d2"},
        }
        count = store.delete_document("d1")
        assert count == 2

    def test_chunks_and_embeddings_mismatch(self, tmp_path):
        store = self._make_store(tmp_path)
        with pytest.raises(ValueError, match="must have same length"):
            store.add([self.make_chunk("c1")], [[0.1] * 384, [0.2] * 384])
