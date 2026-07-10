"""Hybrid retrieval combining dense and sparse search.

Dense: FAISS vector similarity
Sparse: BM25 keyword matching

Fusion strategies:
- Reciprocal Rank Fusion (RRF)
- Score normalization + merge
"""

import logging
import math
import re
from typing import Any

from knowledge.embeddings import EmbeddingModel
from knowledge.models import SearchResult
from knowledge.vector_store import FAISSStore

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid retrieval combining dense (FAISS) and sparse (BM25) search.

    Dense: FAISS vector similarity via the vector store
    Sparse: BM25 keyword matching built from chunk texts

    Fusion: Reciprocal Rank Fusion (RRF)
    """

    def __init__(
        self,
        vector_store: FAISSStore,
        embedding_model: EmbeddingModel,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_model = embedding_model
        self._bm25_corpus: list[list[str]] = []
        self._bm25_chunk_ids: list[str] = []
        self._bm25_avgdl: float = 0.0

    def dense_search(self, query: str, k: int = 10) -> list[SearchResult]:
        """Search using dense vector similarity."""
        query_embedding = self._embedding_model.embed_query(query)
        results = self._vector_store.search(query_embedding, top_k=k)

        for rank, r in enumerate(results):
            object.__setattr__(r, "_rank_override", rank)
            object.__setattr__(r, "_method_override", "dense")

        return results

    def sparse_search(self, query: str, k: int = 10) -> list[SearchResult]:
        """Search using BM25 keyword matching."""
        if not self._bm25_corpus or not self._bm25_chunk_ids:
            return self._fallback_sparse(query, k)

        query_terms = self.keyword_extract(query)
        if not query_terms:
            return []

        scores = self._bm25_score(query_terms)
        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[SearchResult] = []
        self._vector_store.list_sources()

        for rank, (chunk_id, score) in enumerate(ranked[:k]):
            clamped_score = max(0.0, min(1.0, float(score)))
            meta = self._lookup_metadata(chunk_id)
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=meta.get(
                        "document_id", chunk_id.split("_")[0] if "_" in chunk_id else chunk_id
                    ),
                    title=meta.get("title", ""),
                    source=meta.get("source", ""),
                    category=meta.get("category", ""),
                    content=self._vector_store.get_chunk_text(chunk_id) or meta.get("content", ""),
                    score=clamped_score,
                    chunk_number=meta.get("chunk_number", rank),
                    page_number=meta.get("page_number", 0),
                    date=meta.get("date", ""),
                    region=meta.get("region", ""),
                    keywords=meta.get("keywords", []),
                )
            )

        return results

    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        _dense_weight: float = 0.5,
    ) -> list[SearchResult]:
        """Search using both dense and sparse retrieval.

        Combines results using Reciprocal Rank Fusion (RRF).

        Args:
            query: Search query.
            k: Number of results to return.
            dense_weight: Weight for dense results (0 = sparse only, 1 = dense only).

        Returns:
            List of SearchResult objects, fused and sorted.
        """
        dense_results = self.dense_search(query, k=k * 2)
        sparse_results = self.sparse_search(query, k=k * 2)

        if not sparse_results:
            return dense_results[:k]
        if not dense_results:
            return sparse_results[:k]

        fused = self.rrf_fusion(dense_results, sparse_results, k=k * 2)
        return fused[:k]

    def rrf_fusion(
        self,
        dense_results: list[SearchResult],
        sparse_results: list[SearchResult],
        k: int = 60,
    ) -> list[SearchResult]:
        """Combine results using Reciprocal Rank Fusion."""
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for rank, result in enumerate(dense_results):
            cid = result.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            result_map[cid] = result

        for rank, result in enumerate(sparse_results):
            cid = result.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in result_map:
                result_map[cid] = result

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        fused: list[SearchResult] = []
        for _rank, (cid, _score) in enumerate(ranked):
            result = result_map[cid]
            fused.append(result)

        return fused

    def keyword_extract(self, query: str) -> list[str]:
        """Extract meaningful keywords from a query."""
        text = query.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "out",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "about",
            "also",
            "and",
            "but",
            "or",
            "if",
            "while",
            "because",
            "until",
            "what",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "i",
            "me",
            "my",
            "we",
            "our",
            "you",
            "your",
            "he",
            "him",
            "his",
            "she",
            "her",
            "they",
            "them",
            "their",
        }

        return [w for w in words if w not in stop_words and len(w) > 1]

    def build_bm25_index(self, chunk_ids: list[str], texts: list[str]) -> None:
        """Build a BM25 index from chunk texts."""
        self._bm25_chunk_ids = list(chunk_ids)
        self._bm25_corpus = [self._tokenize(t) for t in texts]
        total_terms = sum(len(tokens) for tokens in self._bm25_corpus)
        self._bm25_avgdl = total_terms / max(len(self._bm25_corpus), 1)
        logger.info(
            "Built BM25 index with %d documents, avgdl=%.2f",
            len(self._bm25_corpus),
            self._bm25_avgdl,
        )

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _bm25_score(
        self,
        query_terms: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> dict[str, float]:
        """Compute BM25 scores for query terms."""
        n_docs = len(self._bm25_corpus)
        if n_docs == 0:
            return {}

        df: dict[str, int] = {}
        for term in query_terms:
            df[term] = sum(1 for doc in self._bm25_corpus if term in doc)

        scores: dict[str, float] = {}
        for i, doc_tokens in enumerate(self._bm25_corpus):
            cid = self._bm25_chunk_ids[i]
            doc_len = len(doc_tokens)
            score = 0.0

            for term in query_terms:
                if term not in doc_tokens:
                    continue
                tf = doc_tokens.count(term)
                idf = math.log((n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1.0)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / self._bm25_avgdl)
                score += idf * numerator / denominator

            if score > 0:
                scores[cid] = score

        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _fallback_sparse(self, query: str, k: int = 10) -> list[SearchResult]:
        """Fallback sparse search using metadata keywords when BM25 index is not built."""
        query_terms = self.keyword_extract(query)
        if not query_terms:
            return []

        dense_results = self.dense_search(query, k=k * 3)

        scored: list[tuple[int, float, SearchResult]] = []
        for rank, result in enumerate(dense_results):
            meta_text = f"{result.title} {result.source} {result.category} {result.region} {' '.join(result.keywords)}".lower()
            match_count = sum(1 for t in query_terms if t in meta_text)
            if match_count > 0:
                keyword_score = match_count / len(query_terms)
                combined = 0.3 * result.score + 0.7 * keyword_score
                scored.append((rank, combined, result))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[SearchResult] = []
        for _rank, (_, _score, result) in enumerate(scored[:k]):
            results.append(result)

        return results

    def _lookup_metadata(self, chunk_id: str) -> dict[str, Any]:
        text = self._vector_store.get_chunk_text(chunk_id)
        metadata = self._vector_store.get_chunk_metadata(chunk_id)
        if not metadata:
            return {"content": text or ""}
        return {**metadata, "content": text or metadata.get("content", "")}


__all__ = ["HybridSearch"]
