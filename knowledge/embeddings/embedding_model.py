"""Embedding model wrapper for generating vector representations.

Supports multiple strategies with graceful degradation:
1. Sentence-Transformers (if available) — produces 384/768-dim vectors
2. TF-IDF + TruncatedSVD (sklearn) — fallback
3. Deterministic hash-based dummy embedding — last resort for testing
"""

import logging
import threading
from typing import Any

import numpy as np

from knowledge.config_loader import load_rag_config

logger = logging.getLogger(__name__)

_dummy_embedding_dim: int = 384


def _get_dummy_embedding(text: str, dim: int = 384) -> list[float]:
    import hashlib

    seed = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
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
    """Wrapper around sentence-transformers with fallback strategies.

    Strategies (in order of preference):
    1. Sentence-Transformers — produces 384/768-dim vectors
    2. TF-IDF + SVD (sklearn) — fallback that works without any DL deps
    3. Deterministic hash-based dummy — last resort for testing
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_rag_config()
        rag_cfg = config.get("rag", {})
        self.model_name = rag_cfg.get("embedding_model", "all-MiniLM-L6-v2")
        self.dimension = rag_cfg.get("embedding_dimension", 384)
        self._lock = threading.Lock()
        self._model = None
        self._tfidf_vectorizer: Any = None
        self._svd: Any = None
        self._tfidf_fitted = False
        self._strategy: str = "unknown"
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._strategy = "sentence_transformer"
            logger.info("Using sentence-transformers strategy (model=%s)", self.model_name)
            return
        except ImportError:
            logger.info("sentence-transformers not available, trying TF-IDF fallback")
        except Exception as e:
            logger.warning("Failed to load sentence-transformers: %s", e)

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                sublinear_tf=True,
            )
            self._svd = None
            self._strategy = "tfidf_svd"
            logger.info("Using TF-IDF + SVD embedding strategy")
            return
        except ImportError:
            logger.warning("scikit-learn not available, using dummy embedding fallback")

        self._strategy = "dummy"
        logger.warning("Using dummy embedding strategy (non-functional for search)")

    @property
    def strategy(self) -> str:
        return self._strategy

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        valid_texts = [t if t and t.strip() else " " for t in texts]

        if self._strategy == "sentence_transformer":
            return self._encode_with_st(valid_texts)
        elif self._strategy == "tfidf_svd":
            return self._encode_with_tfidf(valid_texts)
        else:
            return [_get_dummy_embedding(t, self.dimension) for t in valid_texts]

    def _encode_with_st(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def _encode_with_tfidf(self, texts: list[str]) -> list[list[float]]:
        from sklearn.decomposition import TruncatedSVD

        # If texts are too short to produce ≥2 features, fall back to dummy
        # to avoid TruncatedSVD ValueError: "Found array with 1 feature(s)"
        combined_vocab = len(set(" ".join(texts).split()))
        if combined_vocab < 2:
            return [_get_dummy_embedding(t, self.dimension) for t in texts]

        with self._lock:
            if not self._tfidf_fitted:
                tfidf_matrix = self._tfidf_vectorizer.fit_transform(texts)
                n_features = tfidf_matrix.shape[1]
                if n_features < 2:
                    return [_get_dummy_embedding(t, self.dimension) for t in texts]
                actual_dim = min(self.dimension, max(2, n_features - 1))
                self._svd = TruncatedSVD(n_components=actual_dim, random_state=42)
                svd_result = self._svd.fit_transform(tfidf_matrix)
                self._tfidf_fitted = True
            else:
                tfidf_matrix = self._tfidf_vectorizer.transform(texts)
                svd_result = self._svd.transform(tfidf_matrix)

        # Pad to self.dimension if SVD produced fewer components
        if svd_result.shape[1] < self.dimension:
            padded = np.zeros((svd_result.shape[0], self.dimension), dtype=np.float32)
            padded[:, : svd_result.shape[1]] = svd_result
            svd_result = padded

        norms = np.linalg.norm(svd_result, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normalized = svd_result / norms
        # Handle NaN values from degenerate SVD on very short texts
        if np.any(np.isnan(normalized)):
            return [_get_dummy_embedding(t, self.dimension) for t in texts]
        return normalized.astype(np.float32).tolist()

    def encode_single(self, text: str) -> list[float]:
        return self.encode(text)[0]

    def embed_query(self, query: str) -> list[float]:
        return self.encode_single(query)

    def is_available(self) -> bool:
        return self._strategy != "dummy"

    def get_dimension(self) -> int:
        return self.dimension
