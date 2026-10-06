"""Tests for the climatedt.rag facade (ingestion, knowledge base, service)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from climatedt.rag import knowledge_base as kb_module
from climatedt.rag.ingestion import DocumentIngestion
from climatedt.rag.knowledge_base import KnowledgeBase
from climatedt.rag.service import RAGService
from climatedt.rag.service import _wrap_result as service_wrap_result


class _FakeEmbedder:
    def encode(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 4), dtype=np.float32)


@pytest.fixture
def ingestion() -> tuple[DocumentIngestion, MagicMock]:
    store = MagicMock()
    return DocumentIngestion(_FakeEmbedder(), store), store


class TestDocumentIngestion:
    def test_ingests_object_document(self, ingestion) -> None:
        ing, store = ingestion
        doc = SimpleNamespace(
            content="Heavy monsoon rainfall in Karnataka. " * 40,
            title="Monsoon",
            source="IMD",
            document_id="doc-1",
        )

        chunks = ing.ingest(doc)

        assert chunks
        assert all(c.document_id == "doc-1" for c in chunks)
        store.add.assert_called_once()
        added_chunks, embeddings = store.add.call_args.args
        assert len(added_chunks) == len(chunks) == embeddings.shape[0]

    def test_ingests_dict_document_with_defaults(self, ingestion) -> None:
        ing, store = ingestion

        chunks = ing.ingest({"content": "Drought advisory for northern districts."})

        assert chunks
        # A dict without document_id gets a generated, non-empty id.
        assert chunks[0].document_id
        assert store.add.called

    def test_dict_documents_without_id_do_not_collide(self, ingestion) -> None:
        ing, _ = ingestion

        a = ing.ingest({"content": "First advisory."})
        b = ing.ingest({"content": "Second advisory."})

        assert a[0].document_id != b[0].document_id

    def test_ingests_plain_string(self, ingestion) -> None:
        ing, _ = ingestion

        chunks = ing.ingest("Heatwave warning for Kalaburagi.")

        assert chunks[0].content.startswith("Heatwave")


@pytest.fixture
def collections_file(tmp_path, monkeypatch):
    path = tmp_path / "collections.json"
    monkeypatch.setattr(kb_module, "_COLLECTIONS_FILE", str(path))
    return path


class TestKnowledgeBase:
    def _kb(self, metadatas: dict | None = None, results: list | None = None) -> KnowledgeBase:
        store = SimpleNamespace(_metadatas=metadatas or {})
        retrieval = MagicMock()
        retrieval.search.return_value = results or []
        return KnowledgeBase(store, retrieval)

    def test_create_and_list_collections_persist(self, collections_file) -> None:
        kb = self._kb()

        cid = kb.create_collection("Reports", "Govt reports")

        assert collections_file.exists()
        reloaded = self._kb()
        listed = reloaded.list_collections()
        assert [(c.collection_id, c.name) for c in listed] == [(cid, "Reports")]

    def test_corrupt_collections_file_is_ignored(self, collections_file) -> None:
        collections_file.write_text("{not json")

        assert self._kb().list_collections() == []

    async def test_collection_stats_counts_chunks_and_documents(self, collections_file) -> None:
        kb = self._kb(
            metadatas={
                1: {"collection_id": "c1", "document_id": "d1"},
                2: {"collection_id": "c1", "document_id": "d1"},
                3: {"collection_id": "c1", "document_id": "d2"},
                4: {"collection_id": "other", "document_id": "d3"},
            }
        )
        kb._collections["c1"] = {"name": "One", "description": "first"}

        stats = await kb.get_collection_stats("c1")

        assert stats == {
            "name": "One",
            "description": "first",
            "document_count": 2,
            "chunk_count": 3,
        }

    async def test_collection_stats_unknown_collection_raises(self, collections_file) -> None:
        with pytest.raises(ValueError, match="not found"):
            await self._kb().get_collection_stats("missing")

    async def test_search_wraps_results(self, collections_file) -> None:
        hit = SimpleNamespace(
            chunk_id="ch1",
            document_id="d1",
            content="Flood risk text",
            title="T",
            source="S",
            category="C",
            score=0.9,
        )
        kb = self._kb(results=[hit])

        [result] = await kb.search("flood", k=3)

        kb._retrieval.search.assert_called_once_with("flood", top_k=3)
        assert result.score == 0.9
        assert result.chunk.text == "Flood risk text"
        assert result.chunk.metadata == {"title": "T", "source": "S", "category": "C"}


class TestRAGService:
    @pytest.fixture
    def service(self, monkeypatch) -> RAGService:
        api = MagicMock()
        api.get_context.return_value = "context"
        monkeypatch.setattr("climatedt.rag.service.KnowledgeAPI", lambda: api)
        ingestion = MagicMock()
        ingestion.ingest.side_effect = lambda doc: [f"chunk-of-{doc}"]
        knowledge_base = MagicMock()

        async def _search(query, k=5, _collection_id=None):
            return [(query, k, _collection_id)]

        knowledge_base.search.side_effect = _search
        return RAGService(ingestion, MagicMock(), knowledge_base)

    async def test_ask_delegates_to_knowledge_base(self, service) -> None:
        assert await service.ask("rain", k=2, _collection_id="c") == [("rain", 2, "c")]

    async def test_ingest_and_batch(self, service) -> None:
        assert await service.ingest("a") == ["chunk-of-a"]
        doc = SimpleNamespace(document_id="d9")

        batch = await service.ingest_batch([doc])

        assert list(batch) == ["d9"]

    async def test_get_context_uses_api(self, service) -> None:
        assert await service.get_context("q", max_tokens=10) == "context"
        service._api.get_context.assert_called_once_with("q", max_tokens=10)

    def test_wrap_result_truncates_text(self) -> None:
        r = SimpleNamespace(
            chunk_id="c",
            document_id="d",
            content="x" * 900,
            title="t",
            source="s",
            category="k",
            score=0.5,
        )

        wrapped = service_wrap_result(r)

        assert len(wrapped.chunk.text) == 500
        assert wrapped.score == 0.5 and wrapped.rank == 0
