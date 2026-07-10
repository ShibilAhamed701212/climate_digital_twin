"""WP2: Pipeline Profiling.

Measures:
- Stage-level execution time
- Cache hit rates
- Retry counts
- Provider latency
- Identifies bottlenecks
"""

from __future__ import annotations

import asyncio

import pytest

from runtime.benchmarks import benchmark
from runtime.benchmarks.mock_providers import (
    MockLatencyProvider,
    create_mock_registry,
)
from runtime.blackboard import Blackboard
from runtime.cache import TTLCache
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage
from runtime.models.runtime import RuntimeContext
from runtime.pipeline.engine import PipelineEngine
from runtime.providers.executor import run_provider_safely
from runtime.providers.registry import ProviderRegistry

# ── Stage-Level Timing ──────────────────────────────────────────────────


@pytest.mark.profiling
class TestStageExecutionTime:
    """Measure execution time for each stage type."""

    @pytest.mark.asyncio
    async def test_memory_stage(self):
        from runtime.pipeline.stages.memory_stage import MemoryStage

        stage = MemoryStage()
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        result = await benchmark(
            "profiling.memory_stage",
            lambda: stage.execute(ctx),
            iterations=500,
            warmup=50,
        )
        print(f"\n[Profiling MemoryStage] {result}")
        assert result.percentile(99) < 50  # under 50ms

    @pytest.mark.asyncio
    async def test_retrieval_stage(self):
        from runtime.pipeline.stages.retrieval_stage import RetrievalStage

        stage = RetrievalStage()
        registry = create_mock_registry()
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=registry,
            capability_router=CapabilityRouter(),
        )
        ctx.blackboard.publish(
            "retrieval.query", "test query for Bangalore climate", agent="profiling"
        )
        result = await benchmark(
            "profiling.retrieval_stage",
            lambda: stage.execute(ctx),
            iterations=200,
            warmup=20,
        )
        print(f"\n[Profiling RetrievalStage] {result}")

    @pytest.mark.asyncio
    async def test_reasoning_stage(self):
        from runtime.pipeline.stages.reasoning_stage import ReasoningStage

        stage = ReasoningStage()
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=create_mock_registry(),
            capability_router=CapabilityRouter(),
        )
        ctx.blackboard.publish("reasoning.query", "Analyze flood risk trends", agent="profiling")
        result = await benchmark(
            "profiling.reasoning_stage",
            lambda: stage.execute(ctx),
            iterations=200,
            warmup=20,
        )
        print(f"\n[Profiling ReasoningStage] {result}")

    @pytest.mark.asyncio
    async def test_grounding_stage(self):
        from runtime.pipeline.stages.grounding_stage import GroundingStage

        stage = GroundingStage()
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=create_mock_registry(),
            capability_router=CapabilityRouter(),
        )
        result = await benchmark(
            "profiling.grounding_stage",
            lambda: stage.execute(ctx),
            iterations=200,
            warmup=20,
        )
        print(f"\n[Profiling GroundingStage] {result}")


# ── Cache Hit Rate ──────────────────────────────────────────────────────


@pytest.mark.profiling
class TestCacheHitRates:
    """Measure cache hit/miss rates under different access patterns."""

    def test_sequential_access_pattern(self):
        """Sequential access — high hit rate expected."""
        cache = TTLCache[str](max_size=1000, default_ttl=60)
        for i in range(100):
            cache.set(f"key_{i}", f"val_{i}")
        for _ in range(5):
            for i in range(100):
                cache.get(f"key_{i}")
        stats = cache.stats.snapshot()
        print(
            f"\n[Cache Sequential] hits={stats['hits']}, misses={stats['misses']}, rate={stats['hit_rate']:.2%}"
        )
        assert stats["hit_rate"] > 0.99

    def test_random_access_pattern(self):
        """Random access — moderate hit rate."""
        import random

        cache = TTLCache[str](max_size=100, default_ttl=60)
        for i in range(100):
            cache.set(f"key_{i}", f"val_{i}")
        for _ in range(5):
            for _i in range(100):
                cache.get(f"key_{random.randint(0, 199)}")  # some hits, some misses
        stats = cache.stats.snapshot()
        print(
            f"\n[Cache Random] hits={stats['hits']}, misses={stats['misses']}, rate={stats['hit_rate']:.2%}"
        )
        assert stats["hit_rate"] > 0.0

    def test_eviction_behavior(self):
        """Eviction under capacity pressure."""
        cache = TTLCache[str](max_size=50, default_ttl=60)
        for i in range(200):
            cache.set(f"key_{i}", f"val_{i}")
        stats = cache.stats.snapshot()
        print(
            f"\n[Cache Eviction] size={stats['current_size']}, evictions={stats['evictions']}, max_size=50"
        )
        assert stats["evictions"] >= 150
        assert stats["current_size"] <= 50


# ── Retry / Provider Latency ────────────────────────────────────────────


@pytest.mark.profiling
class TestProviderLatency:
    """Measure provider execution latency with variations."""

    @pytest.mark.asyncio
    async def test_fast_provider(self):
        """Fast provider (10ms base)."""
        p = MockLatencyProvider(base_latency_ms=10, jitter_ms=2)
        from runtime.models.provider import ProviderRequest
        from runtime.models.runtime import RuntimeContext

        req = ProviderRequest(capability="mock", params={}, context=RuntimeContext())
        result = await benchmark(
            "provider.fast",
            lambda: run_provider_safely(p.execute, req),
            iterations=200,
            warmup=20,
        )
        print(f"\n[Provider Fast (10ms)] {result}")

    @pytest.mark.asyncio
    async def test_slow_provider(self):
        """Slow provider (100ms base)."""
        p = MockLatencyProvider(base_latency_ms=100, jitter_ms=20)
        from runtime.models.provider import ProviderRequest
        from runtime.models.runtime import RuntimeContext

        req = ProviderRequest(capability="mock", params={}, context=RuntimeContext())
        result = await benchmark(
            "provider.slow",
            lambda: run_provider_safely(p.execute, req),
            iterations=100,
            warmup=10,
        )
        print(f"\n[Provider Slow (100ms)] {result}")

    @pytest.mark.asyncio
    async def test_timeout_provider(self):
        """Provider that times out."""
        from runtime.benchmarks.mock_providers import MockSlowProvider
        from runtime.models.provider import ProviderRequest
        from runtime.models.runtime import RuntimeContext

        p = MockSlowProvider(delay_ms=5000)
        req = ProviderRequest(capability="mock_slow", params={}, context=RuntimeContext())
        result = await benchmark(
            "provider.timeout",
            lambda: run_provider_safely(p.execute, req, timeout_ms=100),
            iterations=20,
            warmup=5,
        )
        print(f"\n[Provider Timeout (100ms timeout)] {result}")


# ── Bottleneck Identification ──────────────────────────────────────────


@pytest.mark.profiling
class TestBottleneckIdentification:
    """Identify which stages contribute most to total latency."""

    @pytest.mark.asyncio
    async def test_stage_latency_breakdown(self):
        """Run full pipeline and break down by stage contribution."""
        engine = PipelineEngine()
        stage_times: dict[str, float] = {}

        stages = []
        for i, (name, delay) in enumerate(
            [
                ("memory", 0.001),
                ("intent", 0.005),
                ("retrieval", 0.020),
                ("planning", 0.010),
                ("grounding", 0.015),
                ("reasoning", 0.025),
                ("execution", 0.030),
                ("response", 0.008),
                ("verification", 0.012),
            ]
        ):

            async def _execute(_self, ctx, n=name, d=delay):
                import time

                t0 = time.perf_counter()
                try:
                    await asyncio.sleep(d)
                finally:
                    elapsed = (time.perf_counter() - t0) * 1000
                    stage_times[n] = elapsed
                ctx.stage_outputs[f"result_{n}"] = "ok"
                return ctx

            s = type(
                f"S{i}",
                (PipelineStage,),
                {
                    "name": name,
                    "dependencies": [],
                    "timeout_ms": 5000,
                    "execute": _execute,
                },
            )
            stages.append(s())

        pipeline = CognitivePipeline(id="profile_pipe", triggers=["x"], stages=stages)
        engine.register(pipeline)
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        await engine.execute(pipeline, ctx)

        total = sum(stage_times.values())
        print(f"\n[Stage Latency Breakdown] Total: {total:.2f}ms")
        for name, t in sorted(stage_times.items(), key=lambda x: -x[1]):
            pct = (t / total * 100) if total > 0 else 0
            print(f"  {name:15s}: {t:.2f}ms ({pct:.1f}%)")
        assert len(stage_times) == 9
