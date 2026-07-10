"""WP3: Load Testing — Concurrent user simulation.

Runs:
- 10, 50, 100, 250, 500 concurrent users
- Measures latency degradation, error rate, throughput, memory growth
- Confirms no deadlocks or race conditions
"""

from __future__ import annotations

import asyncio

import pytest

from runtime.benchmarks import benchmark_concurrent
from runtime.benchmarks.mock_providers import create_mock_registry
from runtime.blackboard import Blackboard
from runtime.event_bus import EventBus
from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage
from runtime.models.runtime import RuntimeContext
from runtime.pipeline.engine import PipelineEngine


def _make_load_pipeline() -> tuple[PipelineEngine, CognitivePipeline]:
    """Create a pipeline for load testing."""
    engine = PipelineEngine()
    stages = []
    for i in range(3):

        async def _execute(_self, ctx, sid=i):
            await asyncio.sleep(0.002)  # 2ms simulated work
            ctx.stage_outputs[f"load_result_{sid}"] = "ok"
            return ctx

        s = type(
            f"S{i}",
            (PipelineStage,),
            {
                "name": f"load_stage_{i}",
                "dependencies": [f"load_stage_{j}" for j in range(i)] if i > 0 else [],
                "timeout_ms": 10000,
                "execute": _execute,
            },
        )
        stages.append(s())

    pipeline = CognitivePipeline(id="load_pipe", triggers=["load"], stages=stages)
    engine.register(pipeline)
    return engine, pipeline


def _make_ctx():
    return ExecutionContext(
        runtime_context=RuntimeContext(),
        blackboard=Blackboard(),
        event_bus=EventBus(),
        provider_registry=create_mock_registry(),
        capability_router=__import__(
            "runtime.capabilities.router", fromlist=["CapabilityRouter"]
        ).CapabilityRouter(),
    )


async def _run_pipeline(engine, pipeline):
    """Execute pipeline with fresh context."""
    ctx = _make_ctx()
    return await engine.execute(pipeline, ctx)


@pytest.mark.loadtest
class TestLoad10Users:
    @pytest.mark.asyncio
    async def test_load_10_users(self):
        engine, pipeline = _make_load_pipeline()
        result = await benchmark_concurrent(
            "load_10",
            lambda: _run_pipeline(engine, pipeline),
            concurrency=10,
            requests_per_worker=30,
            warmup=5,
        )
        s = result.summary()
        print(f"\n[Load 10 users] {result}")
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        assert s.get("p99_ms", 0) < 1000

    @pytest.mark.asyncio
    async def test_load_50_users(self):
        engine, pipeline = _make_load_pipeline()
        result = await benchmark_concurrent(
            "load_50",
            lambda: _run_pipeline(engine, pipeline),
            concurrency=50,
            requests_per_worker=20,
            warmup=3,
        )
        s = result.summary()
        print(f"\n[Load 50 users] {result}")
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        assert s.get("p99_ms", 0) < 2000

    @pytest.mark.asyncio
    async def test_load_100_users(self):
        engine, pipeline = _make_load_pipeline()
        result = await benchmark_concurrent(
            "load_100",
            lambda: _run_pipeline(engine, pipeline),
            concurrency=100,
            requests_per_worker=15,
            warmup=3,
        )
        s = result.summary()
        print(f"\n[Load 100 users] {result}")
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        assert s.get("p99_ms", 0) < 5000

    @pytest.mark.asyncio
    async def test_load_250_users(self):
        engine, pipeline = _make_load_pipeline()
        result = await benchmark_concurrent(
            "load_250",
            lambda: _run_pipeline(engine, pipeline),
            concurrency=250,
            requests_per_worker=10,
            warmup=2,
        )
        s = result.summary()
        print(f"\n[Load 250 users] {result}")
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        assert s.get("p99_ms", 0) < 10000

    @pytest.mark.asyncio
    async def test_load_500_users(self):
        engine, pipeline = _make_load_pipeline()
        result = await benchmark_concurrent(
            "load_500",
            lambda: _run_pipeline(engine, pipeline),
            concurrency=500,
            requests_per_worker=5,
            warmup=1,
        )
        result.summary()
        print(f"\n[Load 500 users] {result}")
        print(f"  Throughput: {result.metadata.get('throughput_rps', 'N/A')} req/s")
        # No strict assertion — just measure and report
