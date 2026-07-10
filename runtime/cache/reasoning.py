"""Reasoning cache — caches evidence hash → ReasoningOutput.

TTL: 600s default (reasoning is expensive to recompute)
Invalidation: by evidence graph hash, or full flush
"""

from __future__ import annotations

from runtime.cache.base import TTLCache
from runtime.models.reasoning import ReasoningOutput


class ReasoningCache:
    """Caches reasoning outputs by evidence graph content hash.

    Reasoning is expensive (rule-based + graph-based + aggregation).
    Cache prevents redundant computation for identical evidence sets.
    """

    def __init__(self, max_size: int = 200, default_ttl: float = 600.0):
        self._cache: TTLCache[ReasoningOutput] = TTLCache(
            max_size=max_size, default_ttl=default_ttl
        )

    @staticmethod
    def _key(evidence_hash: str, strategy: str) -> str:
        return f"{evidence_hash}:{strategy}"

    def get(self, evidence_hash: str, strategy: str = "rule_based") -> ReasoningOutput | None:
        return self._cache.get(self._key(evidence_hash, strategy))

    def set(
        self,
        evidence_hash: str,
        output: ReasoningOutput,
        strategy: str = "rule_based",
        ttl: float | None = None,
    ) -> None:
        self._cache.set(self._key(evidence_hash, strategy), output, ttl)

    def invalidate_all(self) -> int:
        return self._cache.invalidate_all()

    @property
    def stats(self):
        return self._cache.stats

    def snapshot(self) -> dict:
        return self._cache.snapshot()
