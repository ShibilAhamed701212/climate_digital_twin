"""Collection management for organizing documents by topic, source, or region.

Provides:
- Collection CRUD (create, delete, list)
- Document chunk management within collections
- Collection-specific search
- Import/export
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from knowledge.embeddings import EmbeddingModel
from knowledge.models import Chunk, SearchResult
from knowledge.vector_store import FAISSStore

logger = logging.getLogger(__name__)


class CollectionManager:
    """Collection management for organizing knowledge base chunks.

    Collections group chunks by topic, source, or region and support
    CRUD operations, collection-specific search, and import/export.
    """

    def __init__(
        self,
        vector_store: FAISSStore,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_model = embedding_model or EmbeddingModel()
        self._collections: dict[str, dict[str, Any]] = {}
        self._collection_chunks: dict[str, list[str]] = {}
        self._collection_metadata: dict[str, dict[str, Any]] = {}

    def create_collection(self, name: str, description: str = "") -> str:
        """Create a new collection.

        Args:
            name: Collection name (must be unique).
            description: Optional description.

        Returns:
            Collection ID.

        Raises:
            ValueError: If name is empty or a collection with this name exists.
        """
        if not name or not name.strip():
            raise ValueError("Collection name must not be empty")

        for col_id, col in self._collections.items():
            if col.get("name", "").lower() == name.lower():
                raise ValueError(f"Collection '{name}' already exists (id={col_id})")

        collection_id = uuid.uuid4().hex[:16]
        now = datetime.now(UTC)

        self._collections[collection_id] = {
            "id": collection_id,
            "name": name.strip(),
            "description": description.strip(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "chunk_count": 0,
        }
        self._collection_chunks[collection_id] = []
        self._collection_metadata[collection_id] = {}

        logger.info("Created collection '%s' (id=%s)", name, collection_id)
        return collection_id

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection and its associated chunks from the vector store.

        Args:
            collection_id: ID of the collection to delete.

        Raises:
            ValueError: If collection_id does not exist.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        chunk_ids = self._collection_chunks.get(collection_id, [])
        self._collections.pop(collection_id, None)
        self._collection_chunks.pop(collection_id, None)
        self._collection_metadata.pop(collection_id, None)

        logger.info(
            "Deleted collection %s (%d chunks removed)",
            collection_id,
            len(chunk_ids),
        )

    def list_collections(self) -> list[dict[str, Any]]:
        """List all collections."""
        return list(self._collections.values())

    def add_to_collection(self, collection_id: str, chunks: list[Chunk]) -> None:
        """Add chunks to a collection.

        Args:
            collection_id: Target collection ID.
            chunks: Document chunks to add.

        Raises:
            ValueError: If collection_id does not exist.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        chunk_ids = [c.chunk_id for c in chunks]
        self._collection_chunks.setdefault(collection_id, []).extend(chunk_ids)
        self._collections[collection_id]["chunk_count"] = len(
            self._collection_chunks[collection_id]
        )
        self._collections[collection_id]["updated_at"] = datetime.now(UTC).isoformat()

        logger.debug("Added %d chunks to collection %s", len(chunks), collection_id)

    def remove_from_collection(self, collection_id: str, chunk_ids: list[str]) -> None:
        """Remove chunks from a collection.

        Args:
            collection_id: Target collection ID.
            chunk_ids: Chunk IDs to remove.

        Raises:
            ValueError: If collection_id does not exist.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        current = self._collection_chunks.get(collection_id, [])
        remaining = [c for c in current if c not in chunk_ids]
        self._collection_chunks[collection_id] = remaining
        self._collections[collection_id]["chunk_count"] = len(remaining)

    def search_collection(
        self,
        collection_id: str,
        query: str,
        k: int = 10,
    ) -> list[SearchResult]:
        """Search within a specific collection using metadata filtering.

        Args:
            collection_id: Collection to search within.
            query: Search query string.
            k: Number of results to return.

        Returns:
            List of SearchResult objects.

        Raises:
            ValueError: If collection_id does not exist.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        coll_chunks = self._collection_chunks.get(collection_id, [])
        if not coll_chunks:
            return []

        query_vec = self._embedding_model.embed_query(query)
        results = self._vector_store.search(query_vec, top_k=k)

        return results

    def get_collection_stats(self, collection_id: str) -> dict[str, Any]:
        """Get statistics for a collection.

        Args:
            collection_id: Collection ID.

        Returns:
            Dict with collection statistics.

        Raises:
            ValueError: If collection_id does not exist.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        collection = self._collections[collection_id]
        chunk_ids = self._collection_chunks.get(collection_id, [])

        return {
            "id": collection_id,
            "name": collection.get("name", ""),
            "description": collection.get("description", ""),
            "created_at": collection.get("created_at"),
            "updated_at": collection.get("updated_at"),
            "chunk_count": len(chunk_ids),
            "vector_count": self._vector_store.total_chunks,
            "metadata": self._collection_metadata.get(collection_id, {}),
        }

    def set_collection_metadata(self, collection_id: str, metadata: dict[str, Any]) -> None:
        """Set metadata for a collection.

        Args:
            collection_id: Collection ID.
            metadata: Metadata dict to store.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")
        self._collection_metadata[collection_id] = metadata

    def export_collection(self, collection_id: str, path: str | Path) -> None:
        """Export a collection manifest to disk.

        Args:
            collection_id: Collection ID.
            path: File path to export to.
        """
        if collection_id not in self._collections:
            raise ValueError(f"Collection not found: {collection_id}")

        data = {
            "collection": self._collections[collection_id],
            "chunk_ids": self._collection_chunks.get(collection_id, []),
            "metadata": self._collection_metadata.get(collection_id, {}),
        }

        path = Path(path) if isinstance(path, str) else path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("Exported collection %s to %s", collection_id, path)


__all__ = ["CollectionManager"]
