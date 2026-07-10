"""Unit tests for CollectionManager."""

from unittest.mock import MagicMock

import pytest

from knowledge.models import Chunk


def make_chunk(chunk_id="c1", doc_id="d1", content="test content", chunk_number=1):
    return Chunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        title="Doc",
        source="src",
        category="general",
        content=content,
        chunk_number=chunk_number,
    )


class TestCollectionManager:
    def _make_manager(self):
        from knowledge.collections.collection_manager import CollectionManager

        vector_store = MagicMock()
        embedding_model = MagicMock()
        embedding_model.embed_query.return_value = [0.1] * 384
        return CollectionManager(vector_store, embedding_model), vector_store

    def test_create_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test-collection", "A test collection")
        assert cid is not None
        assert len(cid) > 0

    def test_create_collection_empty_name_raises(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="must not be empty"):
            mgr.create_collection("")

    def test_create_collection_duplicate_raises(self):
        mgr, vs = self._make_manager()
        mgr.create_collection("my-collection")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_collection("my-collection")

    def test_create_collection_duplicate_case_insensitive(self):
        mgr, vs = self._make_manager()
        mgr.create_collection("MyCollection")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_collection("mycollection")

    def test_list_collections_empty(self):
        mgr, vs = self._make_manager()
        cols = mgr.list_collections()
        assert cols == []

    def test_list_collections(self):
        mgr, vs = self._make_manager()
        mgr.create_collection("col1", "First collection")
        mgr.create_collection("col2", "Second collection")
        cols = mgr.list_collections()
        assert len(cols) == 2
        names = [c["name"] for c in cols]
        assert "col1" in names
        assert "col2" in names

    def test_delete_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test")
        mgr.delete_collection(cid)
        assert mgr.list_collections() == []

    def test_delete_collection_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.delete_collection("nonexistent")

    def test_add_to_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test")
        mgr.add_to_collection(cid, [make_chunk("c1"), make_chunk("c2")])
        stats = mgr.get_collection_stats(cid)
        assert stats["chunk_count"] == 2

    def test_add_to_collection_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.add_to_collection("bad", [make_chunk("c1")])

    def test_remove_from_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test")
        mgr.add_to_collection(cid, [make_chunk("c1"), make_chunk("c2"), make_chunk("c3")])
        mgr.remove_from_collection(cid, ["c1", "c3"])
        stats = mgr.get_collection_stats(cid)
        assert stats["chunk_count"] == 1

    def test_remove_from_collection_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.remove_from_collection("bad", ["c1"])

    def test_search_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test")
        vs.search.return_value = []
        results = mgr.search_collection(cid, "test query", k=5)
        assert results is not None

    def test_search_collection_empty(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("empty")
        results = mgr.search_collection(cid, "test", k=5)
        assert results == []

    def test_search_collection_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.search_collection("bad", "test")

    def test_get_collection_stats(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test", "desc")
        vs.total_chunks = 10
        stats = mgr.get_collection_stats(cid)
        assert stats["name"] == "test"
        assert stats["description"] == "desc"
        assert stats["vector_count"] == 10

    def test_get_collection_stats_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.get_collection_stats("bad")

    def test_set_collection_metadata(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test")
        mgr.set_collection_metadata(cid, {"region": "Karnataka", "year": 2024})
        stats = mgr.get_collection_stats(cid)
        assert stats["metadata"]["region"] == "Karnataka"

    def test_set_collection_metadata_nonexistent(self):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.set_collection_metadata("bad", {"key": "val"})

    def test_export_collection(self, tmp_path):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("test-export")
        export_path = tmp_path / "export.json"
        mgr.export_collection(cid, str(export_path))
        assert export_path.exists()
        import json

        data = json.loads(export_path.read_text())
        assert data["collection"]["name"] == "test-export"

    def test_export_collection_nonexistent(self, tmp_path):
        mgr, vs = self._make_manager()
        with pytest.raises(ValueError, match="not found"):
            mgr.export_collection("bad", str(tmp_path / "out.json"))

    def test_collection_count_tracking(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("count-test")
        mgr.add_to_collection(cid, [make_chunk("c1"), make_chunk("c2")])
        c1 = mgr.get_collection_stats(cid)["chunk_count"]
        mgr.add_to_collection(cid, [make_chunk("c3")])
        c2 = mgr.get_collection_stats(cid)["chunk_count"]
        assert c1 == 2
        assert c2 == 3

    def test_duplicate_chunks_in_collection(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("dup-test")
        mgr.add_to_collection(cid, [make_chunk("c1"), make_chunk("c1")])
        stats = mgr.get_collection_stats(cid)
        assert stats["chunk_count"] == 2

    def test_collection_creation_timestamps(self):
        mgr, vs = self._make_manager()
        cid = mgr.create_collection("timed")
        stats = mgr.get_collection_stats(cid)
        assert stats["created_at"] is not None
        assert stats["updated_at"] is not None
