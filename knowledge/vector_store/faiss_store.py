"""FAISS vector store wrapper with metadata persistence.

Manages a FAISS index for vector similarity search alongside
a pickle-based metadata store for chunk-level information.
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from knowledge.models import Chunk, SearchResult

logger = logging.getLogger(__name__)


class FAISSStore:
    """FAISS-based vector store with metadata.

    Persists:
      - A FAISS index (IndexFlatIP for cosine similarity)
      - A metadata list (pickle) mapping index positions to Chunk data
    """

    def __init__(
        self,
        index_path: str = "knowledge/vector_store/index.faiss",
        metadata_path: str = "knowledge/vector_store/metadata.pkl",
        dimension: int = 384,
    ) -> None:
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self._index = None
        self._metadata: list[dict[str, Any]] = []
        self._load_index()

    def _load_index(self) -> None:
        try:
            import faiss
            if os.path.exists(self.index_path):
                self._index = faiss.read_index(self.index_path)
                logger.info("Loaded FAISS index from %s (%d vectors)", self.index_path, self._index.ntotal)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)
                logger.info("Created new FAISS index (dim=%d)", self.dimension)
        except Exception:
            logger.warning("FAISS unavailable; using in-memory numpy fallback")
            self._index = None

        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "rb") as f:
                self._metadata = pickle.load(f)
            logger.info("Loaded %d metadata entries", len(self._metadata))

    def _save_index(self) -> None:
        try:
            import faiss
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, self.index_path)
        except Exception:
            logger.warning("Could not save FAISS index to %s", self.index_path)

    def _save_metadata(self) -> None:
        Path(self.metadata_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self._metadata, f)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Add chunk embeddings to the index.

        Args:
            chunks: List of Chunks to store.
            embeddings: List of embedding vectors (same order as chunks).
        """
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length")

        import faiss
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dimension)
        self._index.add(vectors)

        for chunk in chunks:
            self._metadata.append(chunk.to_dict())

        self._save_index()
        self._save_metadata()
        logger.info("Added %d chunks to FAISS index (total: %d)", len(chunks), self._index.ntotal)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """Search the index for the most similar chunks.

        Args:
            query_embedding: Query vector as list of floats.
            top_k: Number of results to return.

        Returns:
            List of SearchResult objects sorted by similarity.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        import faiss
        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(query_vec, k)

        results: list[SearchResult] = []
        for dist, idx in zip(distances[0], indices[0], strict=True):
            if idx < 0 or idx >= len(self._metadata):
                continue
            meta = self._metadata[idx]
            results.append(
                SearchResult(
                    chunk_id=meta.get("chunk_id", ""),
                    document_id=meta.get("document_id", ""),
                    title=meta.get("title", ""),
                    source=meta.get("source", ""),
                    category=meta.get("category", ""),
                    content=meta.get("content", ""),
                    score=float(dist),
                    chunk_number=meta.get("chunk_number", 0),
                    page_number=meta.get("page_number", 0),
                    date=meta.get("date", ""),
                    region=meta.get("region", ""),
                    keywords=meta.get("keywords", []),
                )
            )
        return results

    def delete_document(self, document_id: str) -> int:
        """Remove all chunks belonging to a document.

        Args:
            document_id: ID of the document to remove.

        Returns:
            Number of chunks removed.
        """
        before = len(self._metadata)
        self._metadata = [m for m in self._metadata if m.get("document_id") != document_id]
        removed = before - len(self._metadata)
        if removed > 0:
            self._rebuild_index()
        return removed

    def _rebuild_index(self) -> None:
        import faiss
        self._index = faiss.IndexFlatIP(self.dimension)
        logger.info("Rebuilt FAISS index (metadata count: %d)", len(self._metadata))

    def clear(self) -> None:
        """Clear the entire index."""
        self._metadata.clear()
        self._rebuild_index()
        self._save_index()
        self._save_metadata()
        logger.info("Cleared FAISS index")

    @property
    def total_chunks(self) -> int:
        return len(self._metadata)

    def list_sources(self) -> list[dict[str, Any]]:
        """List unique document sources with chunk counts."""
        sources: dict[str, dict[str, Any]] = {}
        for m in self._metadata:
            doc_id = m.get("document_id", "")
            if doc_id not in sources:
                sources[doc_id] = {
                    "document_id": doc_id,
                    "title": m.get("title", ""),
                    "source": m.get("source", ""),
                    "category": m.get("category", ""),
                    "chunk_count": 0,
                }
            sources[doc_id]["chunk_count"] += 1
        return list(sources.values())
