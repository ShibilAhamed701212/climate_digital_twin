import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from climatedt.rag.retrieval import RetrievalService
from knowledge.vector_store.faiss_store import FAISSStore

_logger = logging.getLogger(__name__)
_COLLECTIONS_FILE = os.environ.get("COLLECTIONS_FILE", "/app/data/collections.json")


class KnowledgeBase:
    def __init__(
        self,
        vector_store: FAISSStore,
        retrieval_service: RetrievalService,
    ) -> None:
        self._store = vector_store
        self._retrieval = retrieval_service
        self._collections: dict[str, dict[str, Any]] = {}
        self._load_collections()

    def _collections_path(self) -> Path:
        return Path(_COLLECTIONS_FILE)

    def _load_collections(self) -> None:
        path = self._collections_path()
        if path.exists():
            try:
                with open(path) as f:
                    self._collections = json.load(f)
                _logger.info("Loaded %d collections from %s", len(self._collections), path)
            except Exception as e:
                _logger.warning("Could not load collections: %s", e)
                self._collections = {}

    def _save_collections(self) -> None:
        path = self._collections_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._collections, f, indent=2)

    def list_collections(self) -> list[Any]:
        class _Collection:
            def __init__(self, cid: str, meta: dict[str, Any]) -> None:
                self.collection_id = cid
                self.name = meta.get("name", cid)

        return [_Collection(cid, meta) for cid, meta in self._collections.items()]

    def create_collection(self, _name: str, _description: str = "") -> str:
        cid = f"col_{uuid.uuid4().hex[:8]}"
        self._collections[cid] = {"name": _name, "description": _description}
        self._save_collections()
        return cid

    async def get_collection_stats(self, collection_id: str) -> dict[str, Any]:
        meta = self._collections.get(collection_id)
        if meta is None:
            raise ValueError(f"Collection '{collection_id}' not found")
        # Count chunks belonging to this collection
        chunk_count = 0
        doc_ids = set()
        for chunk_meta in self._store._metadatas.values():
            if chunk_meta.get("collection_id") == collection_id:
                chunk_count += 1
                if chunk_meta.get("document_id"):
                    doc_ids.add(chunk_meta["document_id"])
        return {
            "name": meta.get("name", collection_id),
            "description": meta.get("description", ""),
            "document_count": len(doc_ids),
            "chunk_count": chunk_count,
        }

    async def search(self, query: str, k: int = 5, _collection_id: str | None = None) -> list[Any]:
        results = self._retrieval.search(query, top_k=k)
        return [_wrap_result(r) for r in results]


def _wrap_result(r: Any) -> Any:
    class WrappedChunk:
        def __init__(self) -> None:
            self.chunk_id = getattr(r, "chunk_id", "")
            self.document_id = getattr(r, "document_id", "")
            self.text = getattr(r, "content", "")
            self.metadata = {
                "title": getattr(r, "title", ""),
                "source": getattr(r, "source", ""),
                "category": getattr(r, "category", ""),
            }

    class WrappedResult:
        def __init__(self) -> None:
            self.chunk = WrappedChunk()
            self.score = getattr(r, "score", 0.0)
            self.rank = 0

    return WrappedResult()
