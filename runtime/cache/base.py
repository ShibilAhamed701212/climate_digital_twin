"""Base caching primitives shared across all Runtime caches."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheStats:
    """Statistics for a single cache instance."""

    hits: int = 0
    misses: int = 0
    current_size: int = 0
    max_size: int = 0
    evictions: int = 0
    invalidations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "current_size": self.current_size,
            "max_size": self.max_size,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
        }


@dataclass
class TTLBucket(Generic[T]):
    """A cache entry with TTL tracking."""

    key: str
    value: T
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0
    access_count: int = 0

    @property
    def expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


class TTLCache(Generic[T]):
    """Thread-safe TTL-based cache with statistics tracking.

    Supports:
    - TTL-based expiry
    - LRU-like eviction when max_size reached
    - Cache statistics (hits, misses, evictions, hit rate)
    - Bulk operations (get_or_compute, invalidate, invalidate_all)
    - Iteration over non-expired entries
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
        self._entries: dict[str, TTLBucket[T]] = {}
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> T | None:
        """Get a value by key. Returns None if missing or expired."""
        with self._lock:
            bucket = self._entries.get(key)
            if bucket is None:
                self._stats.misses += 1
                return None
            if bucket.expired:
                del self._entries[key]
                self._stats.evictions += 1
                self._stats.misses += 1
                return None
            bucket.access_count += 1
            self._stats.hits += 1
            self._stats.current_size = len(self._entries)
            return bucket.value

    def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        """Set a value with optional TTL override."""
        with self._lock:
            # Evict oldest entries if at capacity
            if len(self._entries) >= self._max_size and key not in self._entries:
                oldest = min(self._entries.keys(), key=lambda k: self._entries[k].created_at)
                del self._entries[oldest]
                self._stats.evictions += 1

            self._entries[key] = TTLBucket(
                key=key,
                value=value,
                ttl_seconds=ttl_seconds or self._default_ttl,
            )
            self._stats.current_size = len(self._entries)

    def get_or_compute(
        self, key: str, compute: Callable[[], T], ttl_seconds: float | None = None
    ) -> T:
        """Get from cache or compute and store."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value, ttl_seconds)
        return value

    def invalidate(self, key: str) -> bool:
        """Remove a key from cache. Returns True if existed."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                self._stats.invalidations += 1
                self._stats.current_size = len(self._entries)
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys matching a prefix pattern. Returns count."""
        count = 0
        with self._lock:
            keys = [k for k in self._entries if k.startswith(pattern)]
            for k in keys:
                del self._entries[k]
                count += 1
            if count:
                self._stats.invalidations += count
                self._stats.current_size = len(self._entries)
        return count

    def invalidate_all(self) -> int:
        """Clear all entries. Returns previous count."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._stats.invalidations += count
            self._stats.current_size = 0
        return count

    @property
    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.current_size = len(self._entries)
            return self._stats

    def snapshot(self) -> dict[str, Any]:
        """Snapshot of cache state for observability."""
        with self._lock:
            entries = [
                {
                    "key": e.key,
                    "age_seconds": e.age_seconds,
                    "access_count": e.access_count,
                    "expired": e.expired,
                }
                for e in self._entries.values()
            ]
        return {
            "stats": self.stats.snapshot(),
            "entries": entries,
        }
