"""WP1: End-to-End Pipeline Benchmarks.

Measures:
- Cold-start latency (first pipeline execution)
- Warm-start latency (subsequent executions)
- Average request latency
- p50/p95/p99 latency
- Throughput (requests/sec)
- Concurrent throughput
- Memory/CPU (sampled via /proc/self/status)
"""

from __future__ import annotations

import asyncio

import pytest

from runtime.benchmarks import benchmark, benchmark_concurrent
from runtime.benchmarks.mock_providers import (
    create_mock_registry,
)
from runtime.blackboard import Blackboard
from runtime.cache import TTLCache
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage
from runtime.models.runtime import RuntimeContext
from runtime.pipeline.engine import PipelineEngine

# ── Helper: Create a minimal test pipeline ──────────────────────────────


def make_pipeline(
    stage_count: int = 3,
) -> tuple[PipelineEngine, CognitivePipeline, ExecutionContext]:
    """Create a pipeline with N simple echo stages."""
    engine = PipelineEngine()
    ctx = ExecutionContext(
        runtime_context=RuntimeContext(),
        blackboard=Blackboard(),
        event_bus=EventBus(),
        provider_registry=create_mock_registry(),
        capability_router=CapabilityRouter(),
    )

    stages = []
    for i in range(stage_count):

        async def _execute(_self, ctx, sid=i):
            await asyncio.sleep(0.001)  # 1ms simulated work
            ctx.stage_outputs[f"result_{sid}"] = f"ok_{sid}"
            return ctx

        s = type(
            f"Stage{i}",
            (PipelineStage,),
            {
                "name": f"stage_{i}",
                "timeout_ms": 5000,
                "dependencies": [f"stage_{j}" for j in range(i)] if i > 0 else [],
                "execute": _execute,
            },
        )
        stages.append(s())

    pipeline = CognitivePipeline(id="bench_pipeline", triggers=["bench"], stages=stages)
    engine.register(pipeline)
    return engine, pipeline, ctx


# ── Benchmark Tests ─────────────────────────────────────────────────────


@pytest.mark.benchmark
class TestPipelineColdStart:
    """Measure cold-start latency — first pipeline execution."""

    @pytest.mark.asyncio
    async def test_cold_start_3_stages(self):
        """Cold-start with 3-stage pipeline."""
        engine, pipeline, ctx = make_pipeline(3)
        result = await benchmark(
            "cold_start_3",
            lambda: engine.execute(pipeline, ctx),
            iterations=1,
            warmup=0,
        )
        print(f"\n[Cold Start 3 stages] {result}")
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_cold_start_10_stages(self):
        """Cold-start with 10-stage pipeline."""
        engine, pipeline, ctx = make_pipeline(10)
        result = await benchmark(
            "cold_start_10",
            lambda: engine.execute(pipeline, ctx),
            iterations=1,
            warmup=0,
        )
        print(f"\n[Cold Start 10 stages] {result}")
        assert result.count == 1


@pytest.mark.benchmark
class TestPipelineWarmLatency:
    """Measure warm-start latency averaged over many iterations."""

    @pytest.mark.asyncio
    async def test_warm_latency_3_stages_1000x(self):
        """3-stage pipeline, 1000 warm iterations."""
        engine, pipeline, ctx = make_pipeline(3)

        async def run():
            c = ExecutionContext(
                runtime_context=RuntimeContext(),
                blackboard=Blackboard(),
                event_bus=EventBus(),
                provider_registry=create_mock_registry(),
                capability_router=CapabilityRouter(),
            )
            return await engine.execute(pipeline, c)

        result = await benchmark(
            "warm_latency_3_1000",
            run,
            iterations=1000,
            warmup=50,
        )
        s = result.summary()
        print(f"\n[Warm 3-stage x1000] {result}")
        print(f"  Throughput: {result.throughput(120):.0f} req/s (est)")
        assert result.count == 1000
        assert s["p99_ms"] < 200  # 99th percentile under 200ms


@pytest.mark.benchmark
class TestPipelineThroughput:
    """Measure raw throughput without concurrency."""

    @pytest.mark.asyncio
    async def test_throughput_single_user(self):
        """Single-user throughput, 3-stage pipeline."""
        engine, pipeline, ctx = make_pipeline(3)

        async def run():
            c = ExecutionContext(
                runtime_context=RuntimeContext(),
                blackboard=Blackboard(),
                event_bus=EventBus(),
                provider_registry=create_mock_registry(),
                capability_router=CapabilityRouter(),
            )
            return await engine.execute(pipeline, c)

        import time

        start = time.perf_counter()
        for _ in range(100):
            await run()
        duration = time.perf_counter() - start
        throughput = 100 / duration
        print(f"\n[Single-user throughput] {throughput:.1f} req/s over {duration:.2f}s")
        assert throughput > 10  # at least 10 req/s


@pytest.mark.benchmark
class TestConcurrentThroughput:
    """Measure throughput with concurrency."""

    @pytest.mark.asyncio
    async def test_concurrent_10_users(self):
        """10 concurrent users, 50 requests each, 3-stage pipeline."""
        engine, pipeline, _ = make_pipeline(3)

        async def run():
            c = ExecutionContext(
                runtime_context=RuntimeContext(),
                blackboard=Blackboard(),
                event_bus=EventBus(),
                provider_registry=create_mock_registry(),
                capability_router=CapabilityRouter(),
            )
            return await engine.execute(pipeline, c)

        result = await benchmark_concurrent(
            "concurrent_10",
            run,
            concurrency=10,
            requests_per_worker=50,
            warmup=5,
        )
        print(f"\n[Concurrent 10 users] {result}")
        s = result.summary()
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        assert result.count >= 500  # 10 workers x 50 each minus warmup
        assert s["p99_ms"] < 500  # 99th percentile under 500ms

    @pytest.mark.asyncio
    async def test_concurrent_50_users(self):
        """50 concurrent users, 20 requests each."""
        engine, pipeline, _ = make_pipeline(3)

        async def run():
            c = ExecutionContext(
                runtime_context=RuntimeContext(),
                blackboard=Blackboard(),
                event_bus=EventBus(),
                provider_registry=create_mock_registry(),
                capability_router=CapabilityRouter(),
            )
            return await engine.execute(pipeline, c)

        result = await benchmark_concurrent(
            "concurrent_50",
            run,
            concurrency=50,
            requests_per_worker=20,
            warmup=3,
        )
        print(f"\n[Concurrent 50 users] {result}")
        s = result.summary()
        assert result.count >= 1000
        assert s["p99_ms"] < 2000

    @pytest.mark.asyncio
    async def test_concurrent_100_users(self):
        """100 concurrent users, 10 requests each."""
        engine, pipeline, _ = make_pipeline(3)

        async def run():
            c = ExecutionContext(
                runtime_context=RuntimeContext(),
                blackboard=Blackboard(),
                event_bus=EventBus(),
                provider_registry=create_mock_registry(),
                capability_router=CapabilityRouter(),
            )
            return await engine.execute(pipeline, c)

        result = await benchmark_concurrent(
            "concurrent_100",
            run,
            concurrency=100,
            requests_per_worker=10,
            warmup=2,
        )
        print(f"\n[Concurrent 100 users] {result}")
        s = result.summary()
        assert result.count >= 1000
        assert s["p99_ms"] < 5000


@pytest.mark.benchmark
class TestCachePerformance:
    """Measure cache read/write performance."""

    @pytest.mark.asyncio
    async def test_cache_get_set_latency(self):
        """TTLCache get/set latency."""
        cache = TTLCache[str](max_size=10000, default_ttl=60)

        # Set
        result_set = await benchmark(
            "cache.set",
            lambda: cache.set("key_1", "value_1"),
            iterations=1000,
            warmup=100,
        )
        print(f"\n[Cache SET] {result_set}")

        # Get (hit)
        result_get = await benchmark(
            "cache.get_hit",
            lambda: cache.get("key_1"),
            iterations=1000,
            warmup=100,
        )
        print(f"\n[Cache GET (hit)] {result_get}")

        # Get (miss)
        result_miss = await benchmark(
            "cache.get_miss",
            lambda: cache.get("nonexistent"),
            iterations=1000,
            warmup=100,
        )
        print(f"\n[Cache GET (miss)] {result_miss}")

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Verify cache stats are tracked correctly."""
        cache = TTLCache[str](max_size=100, default_ttl=60)
        cache.set("a", "1")
        cache.get("a")  # hit
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats.snapshot()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] > 0.0


@pytest.mark.benchmark
class TestCircuitBreakerLatency:
    """Measure circuit breaker overhead."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self):
        """Circuit breaker overhead when CLOSED."""
        from runtime.reliability import CircuitBreaker

        cb = CircuitBreaker("test_bench", failure_threshold=100, recovery_timeout=60)

        async def fast():
            return "ok"

        result = await benchmark(
            "circuit_breaker.closed",
            lambda: cb.call(fast),
            iterations=1000,
            warmup=50,
        )
        print(f"\n[Circuit Breaker (CLOSED)] {result}")
        s = result.summary()
        assert s["p99_ms"] < 10  # overhead < 10ms
