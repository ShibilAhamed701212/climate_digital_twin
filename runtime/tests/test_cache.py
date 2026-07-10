"""Tests for caching infrastructure."""

import time

from runtime.cache.base import TTLCache
from runtime.cache.provider import ProviderCache
from runtime.cache.reasoning import ReasoningCache
from runtime.cache.resolution import ResolutionCache
from runtime.cache.retrieval import RetrievalCache
from runtime.models.provider import ProviderResult
from runtime.models.reasoning import Conclusion, ConclusionType, ReasoningOutput
from runtime.models.retrieval import RetrievalResult


class TestTTLCache:
    def test_get_set(self):
        cache = TTLCache[str](max_size=100)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = TTLCache[str](max_size=100)
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = TTLCache[str](max_size=100, default_ttl=0.1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_eviction_when_full(self):
        cache = TTLCache[str](max_size=2)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")  # should evict oldest
        assert cache.get("c") == "3"
        # "a" or "b" should be evicted
        assert cache.get("a") is None or cache.get("b") is None

    def test_invalidate(self):
        cache = TTLCache[str](max_size=100)
        cache.set("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.invalidate("key1") is False

    def test_invalidate_pattern(self):
        cache = TTLCache[str](max_size=100)
        cache.set("user:1", "a")
        cache.set("user:2", "b")
        cache.set("other", "c")
        assert cache.invalidate_pattern("user:") == 2
        assert cache.get("user:1") is None
        assert cache.get("other") == "c"

    def test_invalidate_all(self):
        cache = TTLCache[str](max_size=100)
        cache.set("a", "1")
        cache.set("b", "2")
        assert cache.invalidate_all() == 2
        assert cache.get("a") is None

    def test_get_or_compute(self):
        cache = TTLCache[str](max_size=100)
        computed = []
        result = cache.get_or_compute("key1", lambda: computed.append("ran") or "value1")
        assert result == "value1"
        assert len(computed) == 1
        # Second call should use cache
        result2 = cache.get_or_compute("key1", lambda: computed.append("ran") or "value2")
        assert result2 == "value1"
        assert len(computed) == 1

    def test_stats(self):
        cache = TTLCache[str](max_size=100)
        cache.get("missing")  # miss
        cache.set("a", "1")
        cache.get("a")  # hit
        cache.get("a")  # hit
        stats = cache.stats
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == 2 / 3

    def test_thread_safety(self):
        """Basic thread safety check — no crash under concurrent access."""
        import threading

        cache = TTLCache[str](max_size=100)
        errors = []

        def worker():
            try:
                for i in range(100):
                    key = f"k{i}"
                    cache.set(key, f"v{i}")
                    cache.get(key)
                    cache.invalidate(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert len(errors) == 0


class TestRetrievalCache:
    def test_get_set(self):
        cache = RetrievalCache()
        result = RetrievalResult(query="test", chunks=[], total_results=0)
        cache.set("test query", result)
        cached = cache.get("test query")
        assert cached is not None
        assert cached.query == "test"

    def test_normalization(self):
        cache = RetrievalCache()
        result = RetrievalResult(query="test", chunks=[], total_results=0)
        cache.set("  Test QUERY  ", result)
        assert cache.get("test query") is not None

    def test_invalidate(self):
        cache = RetrievalCache()
        result = RetrievalResult(query="test", chunks=[], total_results=0)
        cache.set("test", result)
        cache.invalidate("test")
        assert cache.get("test") is None

    def test_invalidate_prefix(self):
        cache = RetrievalCache()
        for q in ["weather today", "weather tomorrow", "news"]:
            cache.set(q, RetrievalResult(query=q, chunks=[], total_results=0))
        assert cache.invalidate_prefix("weather") == 2
        assert cache.get("weather today") is None
        assert cache.get("news") is not None


class TestProviderCache:
    def test_get_set(self):
        cache = ProviderCache()
        result = ProviderResult(success=True, data={"temp": 30})
        cache.set("forecast", "loc=bangalore", result)
        cached = cache.get("forecast", "loc=bangalore")
        assert cached is not None
        assert cached.data["temp"] == 30

    def test_invalidate_capability(self):
        cache = ProviderCache()
        cache.set("forecast", "loc=bangalore", ProviderResult(success=True, data={}))
        cache.set("risk", "loc=bangalore", ProviderResult(success=True, data={}))
        cache.set("forecast", "loc=mysore", ProviderResult(success=True, data={}))
        assert cache.invalidate_capability("forecast") == 2
        assert cache.get("forecast", "loc=bangalore") is None
        assert cache.get("risk", "loc=bangalore") is not None


class TestReasoningCache:
    def test_get_set(self):
        cache = ReasoningCache()
        output = ReasoningOutput(
            conclusions=[
                Conclusion(statement="test", confidence=0.9, conclusion_type=ConclusionType.DIRECT)
            ]
        )
        cache.set("ev_hash", output)
        cached = cache.get("ev_hash")
        assert cached is not None
        assert cached.conclusions[0].statement == "test"


class TestResolutionCache:
    def test_compose(self):
        cache = ResolutionCache()
        cache.set_compose("risk", ["forecast", "risk"])
        assert cache.get_compose("risk") == ["forecast", "risk"]

    def test_resolve(self):
        cache = ResolutionCache()
        chain = [("forecast", "forecast_provider")]
        cache.set_resolve("forecast", chain)
        assert cache.get_resolve("forecast") == chain

    def test_invalidate_all(self):
        cache = ResolutionCache()
        cache.set_compose("a", ["a"])
        cache.set_resolve("a", [("a", "p")])
        assert cache.invalidate_all() > 0
        assert cache.get_compose("a") is None
