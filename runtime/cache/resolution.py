"""Capability resolution cache — caches capability → provider chains.

The capability dependency map is immutable after registration, so this cache
never needs TTL-based invalidation — only explicit flush on re-registration.
"""

from __future__ import annotations

from runtime.cache.base import TTLCache


class ResolutionCache:
    """Caches capability resolution chains (compose + resolve_chain).

    Since capability metadata is immutable after registration, resolution
    results never expire naturally. Cache is invalidated only when
    capabilities are re-registered.
    """

    def __init__(self, max_size: int = 100, default_ttl: float = 3600.0):
        self._compose_cache: TTLCache[list[str]] = TTLCache(
            max_size=max_size, default_ttl=default_ttl
        )
        self._resolve_cache: TTLCache[list[tuple]] = TTLCache(
            max_size=max_size, default_ttl=default_ttl
        )

    def get_compose(self, capability: str) -> list[str] | None:
        return self._compose_cache.get(capability)

    def set_compose(self, capability: str, chain: list[str]) -> None:
        # No TTL — immutable after registration; 86400s = 24h practically infinite
        self._compose_cache.set(capability, chain, ttl_seconds=86400.0)

    def get_resolve(self, capability: str) -> list[tuple] | None:
        return self._resolve_cache.get(capability)

    def set_resolve(self, capability: str, chain: list[tuple]) -> None:
        self._resolve_cache.set(capability, chain, ttl_seconds=86400.0)

    def invalidate_all(self) -> int:
        c1 = self._compose_cache.invalidate_all()
        c2 = self._resolve_cache.invalidate_all()
        return c1 + c2

    @property
    def compose_stats(self):
        return self._compose_cache.stats

    @property
    def resolve_stats(self):
        return self._resolve_cache.stats
