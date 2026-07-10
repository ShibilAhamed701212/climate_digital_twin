"""Tests for PipelineEngine, ExecutionContext, and CognitivePipeline."""

import pytest

from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage
from runtime.models.runtime import RuntimeContext
from runtime.pipeline.engine import PipelineEngine
from runtime.providers.registry import ProviderRegistry


class TestExecutionContext:
    def test_create(self):
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        assert ctx.regenerate_count == 0
        assert len(ctx.errors) == 0

    def test_log_stage(self):
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        ctx.log_stage("test", "started")
        assert len(ctx.trace) == 1
        assert ctx.trace[0]["stage"] == "test"
        assert ctx.trace[0]["status"] == "started"

    def test_add_error(self):
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        ctx.add_error("stage1", "something broke")
        assert len(ctx.errors) == 1
        assert ctx.errors[0]["stage"] == "stage1"

    def test_add_metric(self):
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        ctx.add_metric("response_time", 42.0)
        assert ctx.metrics["response_time"] == 42.0


class TestPipelineStage:
    def test_stage_requires_name(self):
        class MyStage(PipelineStage):
            name = "my_stage"

            async def execute(self, ctx):
                return ctx

        s = MyStage()
        assert s.name == "my_stage"
        assert s.dependencies == []


class TestPipelineEngine:
    def test_register_and_find(self):
        engine = PipelineEngine()
        stages = []
        pipeline = CognitivePipeline(id="test", triggers=["user_query"], stages=stages)
        engine.register(pipeline)
        found = engine.find("user_query")
        assert found is not None
        assert found.id == "test"

    def test_find_nonexistent(self):
        engine = PipelineEngine()
        assert engine.find("nonexistent") is None

    def test_resolve_execution_order_sequential(self):
        engine = PipelineEngine()
        stage_a = _make_stage("a", [])
        stage_b = _make_stage("b", ["a"])
        stage_c = _make_stage("c", ["b"])
        layers = engine.resolve_execution_order([stage_a, stage_b, stage_c])
        assert len(layers) == 3
        assert layers[0][0].name == "a"
        assert layers[1][0].name == "b"
        assert layers[2][0].name == "c"

    def test_resolve_execution_order_parallel(self):
        engine = PipelineEngine()
        stage_a = _make_stage("a", [])
        stage_b = _make_stage("b", [])
        stage_c = _make_stage("c", ["a", "b"])
        layers = engine.resolve_execution_order([stage_a, stage_b, stage_c])
        assert len(layers) == 2
        assert len(layers[0]) == 2  # a and b in parallel
        assert layers[1][0].name == "c"

    @pytest.mark.asyncio
    async def test_execute_empty_pipeline(self):
        engine = PipelineEngine()
        ctx = _make_context()
        pipeline = CognitivePipeline(id="empty", triggers=["x"], stages=[])
        result = await engine.execute(pipeline, ctx)
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_single_stage(self):
        engine = PipelineEngine()
        ctx = _make_context()

        class EchoStage(PipelineStage):
            name = "echo"

            async def execute(self, ctx):
                ctx.stage_outputs["echo"] = "hello"
                return ctx

        pipeline = CognitivePipeline(id="echo", triggers=["x"], stages=[EchoStage()])
        result = await engine.execute(pipeline, ctx)
        assert result.stage_outputs["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_execute_stage_timeout(self):
        engine = PipelineEngine()
        ctx = _make_context()

        class SlowStage(PipelineStage):
            name = "slow"
            timeout_ms = 100

            async def execute(self, ctx):
                import asyncio

                await asyncio.sleep(10)
                return ctx

        pipeline = CognitivePipeline(id="slow", triggers=["x"], stages=[SlowStage()])
        result = await engine.execute(pipeline, ctx)
        assert len(result.errors) > 0  # timed out

    @pytest.mark.asyncio
    async def test_execute_stage_error(self):
        engine = PipelineEngine()
        ctx = _make_context()

        class BrokenStage(PipelineStage):
            name = "broken"

            async def execute(self, _ctx):
                raise ValueError("broken")

        pipeline = CognitivePipeline(id="err", triggers=["x"], stages=[BrokenStage()])
        result = await engine.execute(pipeline, ctx)
        assert len(result.errors) > 0

    def test_list_triggers(self):
        engine = PipelineEngine()
        p1 = CognitivePipeline(id="p1", triggers=["a", "b"], stages=[])
        p2 = CognitivePipeline(id="p2", triggers=["c"], stages=[])
        engine.register(p1)
        engine.register(p2)
        triggers = engine.list_triggers()
        assert "a" in triggers
        assert "b" in triggers
        assert "c" in triggers


def _make_stage(stage_name: str, deps: list[str]):
    class S(PipelineStage):
        name = stage_name
        dependencies = deps

        async def execute(self, ctx):
            return ctx

    return S()


def _make_context():
    return ExecutionContext(
        runtime_context=RuntimeContext(),
        blackboard=Blackboard(),
        event_bus=EventBus(),
        provider_registry=ProviderRegistry(),
        capability_router=CapabilityRouter(),
    )
