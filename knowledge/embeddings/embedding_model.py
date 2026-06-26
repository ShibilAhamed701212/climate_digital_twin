"""Embedding model wrapper for generating vector representations.

Uses sentence-transformers with a configurable model name.
Falls back to a simple hash-based dummy embedding when the
sentence-transformers package is unavailable (offline mode).
"""

import logging
from typing import Any

from knowledge.config_loader import load_rag_config

logger = logging.getLogger(__name__)

_dummy_embedding_dim: int = 384


def _get_dummy_embedding(text: str, dim: int = 384) -> list[float]:
    """Generate a deterministic dummy embedding based on text hash.

    Used as a fallback when sentence-transformers is not available.
    """
    import hashlib
    seed = hashlib.md5(text.encode()).hexdigest()
    seed_int = int(seed[:8], 16)
    rng = _SimpleRNG(seed_int)
    return [rng.random() for _ in range(dim)]


class _SimpleRNG:
    """Minimal deterministic PRNG for dummy embeddings."""

    def __init__(self, seed: int) -> None:
        self.state = seed

    def random(self) -> float:
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF


class EmbeddingModel:
    """Wrapper around sentence-transformers with fallback.

    Uses the configured embedding model from rag.yaml.
    Falls back to deterministic hash-based embeddings when
    sentence-transformers is unavailable.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_rag_config()
        rag_cfg = config.get("rag", {})
        self.model_name = rag_cfg.get("embedding_model", "all-MiniLM-L6-v2")
        self.dimension = rag_cfg.get("embedding_dimension", 384)
        self._model = None
        self._use_dummy = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("Loaded embedding model: %s", self.model_name)
        except Exception:
            logger.warning(
                "sentence-transformers unavailable; using dummy embeddings (model=%s)",
                self.model_name,
            )
            self._use_dummy = True

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        """Encode text(s) into embedding vectors.

        Args:
            texts: A single string or list of strings.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        if isinstance(texts, str):
            texts = [texts]

        if self._use_dummy:
            return [_get_dummy_embedding(t, self.dimension) for t in texts]

        embeddings = self._model.encode(texts, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def encode_single(self, text: str) -> list[float]:
        """Encode a single text into an embedding vector."""
        return self.encode(text)[0]
