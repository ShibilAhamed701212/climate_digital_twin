"""Retrieval cache — caches query → RetrievalResult mappings.

TTL: 300s default (configurable)
Invalidation: by query prefix, by source, or full flush
"""

from __future__ import annotations

from collections.abc import Callable

from runtime.cache.base import TTLCache
from runtime.models.retrieval import RetrievalResult


class RetrievalCache:
    """Caches retrieval results by query text.

    Uses a normalized query key to maximize cache hits.
    Supports TTL, invalidation by query prefix, and statistics.
    """

    def __init__(self, max_size: int = 500, default_ttl: float = 300.0):
        self._cache: TTLCache[RetrievalResult] = TTLCache(
            max_size=max_size, default_ttl=default_ttl
        )

    @staticmethod
    def _normalize(query: str) -> str:
        """Create a normalized cache key from a query."""
        return query.lower().strip()

    def get(self, query: str) -> RetrievalResult | None:
        """Get cached result for query."""
        return self._cache.get(self._normalize(query))

    def set(self, query: str, result: RetrievalResult, ttl: float | None = None) -> None:
        """Cache result for query."""
        self._cache.set(self._normalize(query), result, ttl)

    def get_or_compute(
        self,
        query: str,
        compute: Callable[[], RetrievalResult],
        ttl: float | None = None,
    ) -> RetrievalResult:
        """Get from cache or compute and store."""
        key = self._normalize(query)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = compute()
        self._cache.set(key, result, ttl)
        return result

    def invalidate(self, query: str) -> bool:
        """Remove a specific query from cache."""
        return self._cache.invalidate(self._normalize(query))

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all queries starting with a prefix."""
        return self._cache.invalidate_pattern(prefix.lower())

    def invalidate_all(self) -> int:
        """Clear entire cache."""
        return self._cache.invalidate_all()

    @property
    def stats(self):
        return self._cache.stats

    def snapshot(self) -> dict:
        return self._cache.snapshot()
