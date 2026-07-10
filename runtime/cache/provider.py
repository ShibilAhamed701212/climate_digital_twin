"""Provider response cache — caches capability+params → ProviderResult.

TTL: 60s default (configurable per capability)
Invalidation: by capability, by id, or full flush
"""

from __future__ import annotations

from collections.abc import Callable

from runtime.cache.base import TTLCache
from runtime.models.provider import ProviderResult


class ProviderCache:
    """Caches provider results by capability + parameter hash.

    Supports per-capability TTL override for providers with different
    staleness requirements (e.g., slow-changing data → 300s, fast-changing → 30s).
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 60.0):
        self._cache: TTLCache[ProviderResult] = TTLCache(max_size=max_size, default_ttl=default_ttl)

    @staticmethod
    def _key(capability: str, params_hash: str) -> str:
        return f"{capability}:{params_hash}"

    def get(self, capability: str, params_hash: str) -> ProviderResult | None:
        return self._cache.get(self._key(capability, params_hash))

    def set(
        self,
        capability: str,
        params_hash: str,
        result: ProviderResult,
        ttl: float | None = None,
    ) -> None:
        self._cache.set(self._key(capability, params_hash), result, ttl)

    def get_or_compute(
        self,
        capability: str,
        params_hash: str,
        compute: Callable[[], ProviderResult],
        ttl: float | None = None,
    ) -> ProviderResult:
        key = self._key(capability, params_hash)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = compute()
        self._cache.set(key, result, ttl)
        return result

    def invalidate_capability(self, capability: str) -> int:
        """Invalidate all entries for a given capability."""
        return self._cache.invalidate_pattern(f"{capability}:")

    def invalidate_all(self) -> int:
        return self._cache.invalidate_all()

    @property
    def stats(self):
        return self._cache.stats

    def snapshot(self) -> dict:
        return self._cache.snapshot()
