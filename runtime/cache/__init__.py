"""Runtime caching infrastructure.

Supports TTL-based caches for:
- Retrieval results (query → chunks)
- Provider responses (capability → result)
- Reasoning outputs (evidence hash → conclusions)
- Capability resolution chains

All caches support:
- TTL expiry
- Manual invalidation
- Cache statistics (hits, misses, size, evictions)
"""

from runtime.cache.base import CacheStats, TTLBucket, TTLCache
from runtime.cache.provider import ProviderCache
from runtime.cache.reasoning import ReasoningCache
from runtime.cache.resolution import ResolutionCache
from runtime.cache.retrieval import RetrievalCache

__all__ = [
    "CacheStats",
    "TTLBucket",
    "TTLCache",
    "RetrievalCache",
    "ProviderCache",
    "ReasoningCache",
    "ResolutionCache",
]
