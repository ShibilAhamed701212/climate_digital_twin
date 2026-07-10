"""FAISS vector store wrapper with metadata persistence.

Manages a FAISS index for vector similarity search alongside
a JSON-based metadata store for chunk-level information.

Supports multiple index types:
- FlatIP (exact search, default)
- IVF (approximate, faster for large indices)
- HNSW (approximate, fast with graph-based search)
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

from knowledge.models import Chunk, SearchResult

logger = logging.getLogger(__name__)


class DebouncedSaver:
    def __init__(self, save_func, delay: float = 2.0):
        self._save_func = save_func
        self._delay = delay
        self._timer = None
        self._lock = threading.Lock()

    def schedule(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._save)
            self._timer.daemon = True
            self._timer.start()

    def _save(self):
        self._save_func()

    def flush(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
        self._save_func()


class FAISSStore:
    """FAISS-based vector store with metadata.

    Features:
    - Index management (create, add, search, delete)
    - Multiple index types (FlatIP, IVF, HNSW)
    - Persistence to disk (save/load FAISS index)
    - Metadata alongside vector search
    - Thread-safe operations

    Uses inner product (IP) for similarity with normalized vectors.
    """

    def __init__(
        self,
        index_path: str = "",
        metadata_path: str = "",
        dimension: int = 384,
        index_type: str = "flat",
    ) -> None:
        if not index_path:
            data_dir = os.environ.get("DATA_DIR", "/app/data")
            index_path = os.path.join(data_dir, "vector_store", "index.faiss")
        if not metadata_path:
            data_dir = os.environ.get("DATA_DIR", "/app/data")
            metadata_path = os.path.join(data_dir, "vector_store", "metadata.pkl")
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self._index_type = index_type.lower()
        self._lock = threading.Lock()
        self._index = None
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_id: dict[int, str] = {}
        self._metadatas: dict[str, dict[str, Any]] = {}
        self._chunk_texts: dict[str, str] = {}
        self._next_idx = 0
        self._debounced_index_save = DebouncedSaver(self._save_index)
        self._debounced_metadata_save = DebouncedSaver(self._save_metadata)
        self._load_index()

    def _build_faiss_index(self):
        import faiss

        if self._index_type == "flat":
            base_index = faiss.IndexFlatIP(self.dimension)
        elif self._index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            n_centroids = int(max(1, min(256, self.dimension**0.5)))
            base_index = faiss.IndexIVFFlat(
                quantizer, self.dimension, n_centroids, faiss.METRIC_INNER_PRODUCT
            )
            n_train = max(1, int(max(1, min(256, self.dimension**0.5))) * 2)
            base_index.train(np.random.randn(n_train, self.dimension).astype(np.float32))
        elif self._index_type == "hnsw":
            base_index = faiss.IndexHNSWFlat(self.dimension, 32)
            base_index.hnsw.efConstruction = 200
        else:
            raise ValueError(
                f"Unknown index_type '{self._index_type}'. Expected 'flat', 'ivf', or 'hnsw'"
            )

        return faiss.IndexIDMap(base_index)

    def _load_index(self) -> None:
        try:
            import faiss

            if os.path.exists(self.index_path):
                self._index = faiss.read_index(self.index_path)
                logger.info(
                    "Loaded FAISS index from %s (%d vectors)", self.index_path, self._index.ntotal
                )
            else:
                self._index = self._build_faiss_index()
                logger.info(
                    "Created new FAISS index (dim=%d, type=%s)", self.dimension, self._index_type
                )
        except Exception:
            logger.warning("FAISS unavailable; using in-memory numpy fallback")
            self._index = None

        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path) as f:
                    data = json.load(f)
                self._id_to_idx = data.get("id_to_idx", {})
                self._idx_to_id = {int(k): v for k, v in data.get("idx_to_id", {}).items()}
                self._metadatas = data.get("metadatas", {})
                self._chunk_texts = data.get("chunk_texts", {})
                self._next_idx = data.get("next_idx", len(self._id_to_idx))
                logger.info("Loaded %d metadata entries", len(self._metadatas))
            except Exception:
                logger.warning("Could not load metadata from %s", self.metadata_path)

    def _save_index(self) -> None:
        try:
            import faiss

            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, self.index_path)
        except Exception:
            logger.warning("Could not save FAISS index to %s", self.index_path)

    def _save_metadata(self) -> None:
        Path(self.metadata_path).parent.mkdir(parents=True, exist_ok=True)
        metadata_payload = {
            "dimension": self.dimension,
            "index_type": self._index_type,
            "next_idx": self._next_idx,
            "id_to_idx": self._id_to_idx,
            "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
            "metadatas": self._metadatas,
            "chunk_texts": self._chunk_texts,
        }
        with open(self.metadata_path, "w") as f:
            json.dump(metadata_payload, f, default=str)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Add chunk embeddings to the index.

        Args:
            chunks: List of Chunks to store.
            embeddings: List of embedding vectors (same order as chunks).
        """
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length"
            )

        vectors = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normalized = vectors / norms

        with self._lock:
            if self._index is None:
                self._index = self._build_faiss_index()

            chunk_ids = [c.chunk_id for c in chunks]
            indices = np.arange(self._next_idx, self._next_idx + len(chunks), dtype=np.int64)

            for i, cid in enumerate(chunk_ids):
                self._id_to_idx[cid] = self._next_idx + i
                self._idx_to_id[self._next_idx + i] = cid

            self._next_idx += len(chunks)
            self._index.add_with_ids(normalized.astype(np.float32), indices)

            for chunk in chunks:
                self._metadatas[chunk.chunk_id] = chunk.to_dict()
                self._chunk_texts[chunk.chunk_id] = chunk.content

        self._debounced_index_save.schedule()
        self._debounced_metadata_save.schedule()
        logger.info("Added %d chunks to FAISS index (total: %d)", len(chunks), self._index.ntotal)

    def add_vectors(
        self,
        chunk_ids: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict[str, Any]] | None = None,
        texts: list[str] | None = None,
    ) -> None:
        """Add vectors directly to the index (low-level API).

        Args:
            chunk_ids: Unique identifiers for each vector.
            embeddings: numpy array of shape (n_vectors, dimension).
            metadatas: Optional metadata dicts for each vector.
            texts: Optional chunk text strings for retrieval.
        """
        if not chunk_ids or embeddings.shape[0] == 0:
            return
        if embeddings.shape[0] != len(chunk_ids):
            raise ValueError(
                f"Number of embeddings ({embeddings.shape[0]}) does not match "
                f"number of chunk_ids ({len(chunk_ids)})"
            )
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension ({embeddings.shape[1]}) does not match "
                f"store dimension ({self.dimension})"
            )

        with self._lock:
            if self._index is None:
                self._index = self._build_faiss_index()

            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            normalized = embeddings / norms

            indices = np.arange(self._next_idx, self._next_idx + len(chunk_ids), dtype=np.int64)
            for i, cid in enumerate(chunk_ids):
                self._id_to_idx[cid] = self._next_idx + i
                self._idx_to_id[self._next_idx + i] = cid

            self._next_idx += len(chunk_ids)
            self._index.add_with_ids(normalized.astype(np.float32), indices)

            if metadatas is not None:
                for cid, meta in zip(chunk_ids, metadatas, strict=False):
                    self._metadatas[cid] = meta
            else:
                for cid in chunk_ids:
                    self._metadatas[cid] = {}

            if texts is not None:
                for cid, text in zip(chunk_ids, texts, strict=False):
                    self._chunk_texts[cid] = text

        self._debounced_index_save.schedule()
        self._debounced_metadata_save.schedule()
        logger.debug("Added %d vectors to store", len(chunk_ids))

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search the index for the most similar chunks.

        Args:
            query_embedding: Query vector as list of floats.
            top_k: Number of results to return.
            metadata_filter: Optional metadata filter dict.

        Returns:
            List of SearchResult objects sorted by similarity.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vec = np.array([query_embedding], dtype=np.float32)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        with self._lock:
            total = self._index.ntotal
            search_k = min(top_k * 4, total) if metadata_filter else min(top_k, total)
            search_k = max(search_k, 1)

            scores, indices = self._index.search(query_vec.astype(np.float32), search_k)

            results: list[SearchResult] = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx == -1:
                    continue
                cid = self._idx_to_id.get(int(idx))
                if cid is None:
                    continue

                if metadata_filter is not None:
                    meta = self._metadatas.get(cid, {})
                    if not all(meta.get(k) == v for k, v in metadata_filter.items()):
                        continue

                meta = self._metadatas.get(cid, {})
                clamped_score = max(0.0, min(1.0, float(score)))
                results.append(
                    SearchResult(
                        chunk_id=cid,
                        document_id=meta.get("document_id", ""),
                        title=meta.get("title", ""),
                        source=meta.get("source", ""),
                        category=meta.get("category", ""),
                        content=self._chunk_texts.get(cid, meta.get("content", "")),
                        score=clamped_score,
                        chunk_number=meta.get("chunk_number", 0),
                        page_number=meta.get("page_number", 0),
                        date=meta.get("date", ""),
                        region=meta.get("region", ""),
                        keywords=meta.get("keywords", []),
                    )
                )

                if len(results) >= top_k:
                    break

        return results

    def delete(self, chunk_ids: list[str]) -> None:
        """Remove specific vectors from the index.

        Args:
            chunk_ids: Identifiers of vectors to remove.
        """
        if not chunk_ids:
            return

        with self._lock:
            indices_to_remove: list[int] = []
            for cid in chunk_ids:
                idx = self._id_to_idx.pop(cid, None)
                if idx is not None:
                    indices_to_remove.append(idx)
                    self._idx_to_id.pop(idx, None)
                    self._metadatas.pop(cid, None)
                    self._chunk_texts.pop(cid, None)

            if indices_to_remove:
                ids_to_remove = np.array(indices_to_remove, dtype=np.int64)
                self._index.remove_ids(ids_to_remove)
                logger.debug("Removed %d vectors from store", len(indices_to_remove))

        self._debounced_index_save.schedule()
        self._debounced_metadata_save.schedule()

    def delete_document(self, document_id: str) -> int:
        """Remove all chunks belonging to a document.

        Args:
            document_id: ID of the document to remove.

        Returns:
            Number of chunks removed.
        """
        chunk_ids = [
            cid for cid, meta in self._metadatas.items() if meta.get("document_id") == document_id
        ]
        if chunk_ids:
            self.delete(chunk_ids)
        return len(chunk_ids)

    def build_index(
        self,
        embeddings: np.ndarray,
        chunk_ids: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        texts: list[str] | None = None,
    ) -> None:
        """Reset and rebuild the index with new embeddings.

        Args:
            embeddings: numpy array of shape (n_vectors, dimension).
            chunk_ids: Optional chunk IDs for each vector.
            metadatas: Optional metadata dicts for each vector.
            texts: Optional text content for each vector.
        """
        with self._lock:
            self._index = self._build_faiss_index()
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            self._metadatas.clear()
            self._chunk_texts.clear()
            self._next_idx = 0

            if len(embeddings) > 0:
                count = len(embeddings)
                ids = chunk_ids or [f"chunk_{i}" for i in range(count)]
                indices = np.arange(count, dtype=np.int64)
                for i, cid in enumerate(ids):
                    self._id_to_idx[cid] = i
                    self._idx_to_id[i] = cid
                self._next_idx = count
                self._index.add_with_ids(embeddings.astype(np.float32), indices)
                for i, cid in enumerate(ids):
                    self._metadatas[cid] = metadatas[i] if metadatas and i < len(metadatas) else {}
                    self._chunk_texts[cid] = texts[i] if texts and i < len(texts) else ""

                logger.info("Rebuilt index with %d vectors", count)

        self._debounced_index_save.schedule()
        self._debounced_metadata_save.schedule()

    def clear(self) -> None:
        """Clear the entire index."""
        with self._lock:
            self._index = self._build_faiss_index()
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            self._metadatas.clear()
            self._chunk_texts.clear()
            self._next_idx = 0

        self._debounced_index_save.schedule()
        self._debounced_metadata_save.schedule()
        logger.info("Cleared FAISS index")

    def get_chunk_text(self, chunk_id: str) -> str:
        """Retrieve the text of a chunk by its ID."""
        return self._chunk_texts.get(chunk_id, "")

    def get_chunk_metadata(self, chunk_id: str) -> dict[str, Any]:
        """Retrieve the metadata of a chunk by its ID."""
        return self._metadatas.get(chunk_id, {})

    def list_sources(self) -> list[dict[str, Any]]:
        """List unique document sources with chunk counts."""
        sources: dict[str, dict[str, Any]] = {}
        for _cid, meta in self._metadatas.items():
            doc_id = meta.get("document_id", "")
            if doc_id not in sources:
                sources[doc_id] = {
                    "document_id": doc_id,
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "category": meta.get("category", ""),
                    "chunk_count": 0,
                }
            sources[doc_id]["chunk_count"] += 1
        return list(sources.values())

    @property
    def total_chunks(self) -> int:
        return len(self._metadatas)

    def __len__(self) -> int:
        return self.total_chunks

    def __contains__(self, chunk_id: str) -> bool:
        return chunk_id in self._id_to_idx
