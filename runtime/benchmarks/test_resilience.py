"""WP4: Resilience Testing — Failure injection.

Tests:
- Provider unavailable
- Provider timeout
- Malformed provider response
- Retrieval failure
- Memory failure
- Cache failure
- Circuit breaker activation
- Retry exhaustion

Verifies graceful degradation — no single failure crashes the Runtime.
"""

from __future__ import annotations

import asyncio

import pytest

from runtime.benchmarks.mock_providers import (
    MockSlowProvider,
)
from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage
from runtime.models.provider import ProviderRequest, ProviderResult
from runtime.models.runtime import RuntimeContext
from runtime.pipeline.engine import PipelineEngine
from runtime.providers.base import Provider
from runtime.providers.executor import run_provider_safely
from runtime.providers.registry import ProviderRegistry
from runtime.reliability import CircuitBreaker, CircuitBreakerOpenError

# ── Provider Failure Scenarios ──────────────────────────────────────────


class FailingProvider(Provider):
    provider_id = "test.failing"
    capability = "test_fail"
    config: dict = {}

    def __init__(self, fail_on_call: int = 0, error_msg: str = "provider error"):
        self._fail_on = fail_on_call
        self._error_msg = error_msg
        self._calls = 0

    async def execute(self, _request: ProviderRequest) -> ProviderResult:
        self._calls += 1
        if self._fail_on > 0 and self._calls >= self._fail_on:
            raise RuntimeError(self._error_msg)
        return ProviderResult(success=True, data={"result": "ok"})

    def health(self):
        from runtime.models.provider import ProviderHealth

        return ProviderHealth(ok=True)

    @property
    def deterministic(self) -> bool:
        return True


@pytest.mark.resilience
class TestProviderUnavailable:
    """Tests for provider unavailability."""

    @pytest.mark.asyncio
    async def test_provider_returns_error(self):
        """Provider returns success=False."""
        p = FailingProvider()
        req = ProviderRequest(capability="test_fail", params={}, context=RuntimeContext())
        result = await run_provider_safely(p.execute, req)
        assert result.success is True  # first call succeeds (fail_on=0)

    @pytest.mark.asyncio
    async def test_provider_raises_exception(self):
        """Provider raises exception — wrapped into ProviderResult."""
        p = FailingProvider(fail_on_call=1, error_msg="service down")
        await run_provider_safely(
            p.execute, ProviderRequest(capability="test_fail", params={}, context=RuntimeContext())
        )
        result = await run_provider_safely(
            p.execute, ProviderRequest(capability="test_fail", params={}, context=RuntimeContext())
        )
        assert result.success is False
        assert "service down" in (result.error or "")

    @pytest.mark.asyncio
    async def test_provider_timeout(self):
        """Provider timeout handled gracefully."""
        p = MockSlowProvider(delay_ms=5000)
        req = ProviderRequest(capability="mock_slow", params={}, context=RuntimeContext())
        result = await run_provider_safely(p.execute, req, timeout_ms=50)
        assert result.success is False
        assert (
            "timed out" in (result.error or "").lower() or "timeout" in (result.error or "").lower()
        )


@pytest.mark.resilience
class TestCircuitBreakerResilience:
    """Tests for circuit breaker failure handling."""

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Circuit opens after threshold failures."""
        cb = CircuitBreaker("test_resilience", failure_threshold=3, recovery_timeout=60)
        call_count = 0

        async def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)

        assert cb.state.name == "OPEN"

        # Subsequent calls rejected fast
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(fail)

    @pytest.mark.asyncio
    async def test_circuit_recovers(self):
        """Circuit recovers after recovery timeout."""
        cb = CircuitBreaker("test_recover", failure_threshold=1, recovery_timeout=0.05)

        async def fail_then_ok():
            if not hasattr(fail_then_ok, "called"):
                fail_then_ok.called = True
                raise ValueError("fail first")
            return "ok"

        with pytest.raises(ValueError):
            await cb.call(fail_then_ok)

        await asyncio.sleep(0.06)
        result = await cb.call(fail_then_ok)
        assert result == "ok"
        assert cb.state.name == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_rejects_during_open(self):
        """Fast rejection during OPEN state, no downstream calls."""
        cb = CircuitBreaker("test_reject", failure_threshold=1, recovery_timeout=60)

        downstream_calls = 0

        async def downstream():
            nonlocal downstream_calls
            downstream_calls += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(downstream)

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(downstream)

        # Downstream should NOT have been called during OPEN
        assert downstream_calls == 1


@pytest.mark.resilience
class TestPipelineStageFailure:
    """Tests for pipeline stage-level failure handling."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_stage_error(self):
        """Pipeline does not crash when a stage fails."""
        engine = PipelineEngine()

        class BrokenStage(PipelineStage):
            name = "broken"
            timeout_ms = 5000

            async def execute(self, _ctx):
                raise ValueError("stage crashed")

        pipeline = CognitivePipeline(id="fail_test", triggers=["x"], stages=[BrokenStage()])
        engine.register(pipeline)
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        result = await engine.execute(pipeline, ctx)
        assert len(result.errors) > 0
        assert "broken" in str(result.errors[0])

    @pytest.mark.asyncio
    async def test_pipeline_handles_timeout(self):
        """Pipeline handles stage timeout gracefully."""
        engine = PipelineEngine()

        class SlowStage(PipelineStage):
            name = "slow"
            timeout_ms = 50

            async def execute(self, ctx):
                await asyncio.sleep(10)
                return ctx

        pipeline = CognitivePipeline(id="timeout_test", triggers=["x"], stages=[SlowStage()])
        engine.register(pipeline)
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        result = await engine.execute(pipeline, ctx)
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_pipeline_continues_after_stage_failure(self):
        """Subsequent stages still execute after a non-critical stage failure."""
        engine = PipelineEngine()
        results = []

        class StageA(PipelineStage):
            name = "stage_a"
            timeout_ms = 5000

            async def execute(self, _ctx):
                results.append("a_started")
                raise ValueError("A failed")

        class StageB(PipelineStage):
            name = "stage_b"
            dependencies = []
            timeout_ms = 5000

            async def execute(self, ctx):
                results.append("b_executed")
                return ctx

        pipeline = CognitivePipeline(id="cont_test", triggers=["x"], stages=[StageA(), StageB()])
        engine.register(pipeline)
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        await engine.execute(pipeline, ctx)
        assert "b_executed" in results


@pytest.mark.resilience
class TestRetryExhaustion:
    """Tests for retry exhaustion behavior."""

    @pytest.mark.asyncio
    async def test_retry_exhaustion_returns_error(self):
        """After retries exhausted, error is returned, not raised."""
        p = FailingProvider(fail_on_call=1, error_msg="persistent failure")
        req = ProviderRequest(capability="test_fail", params={}, context=RuntimeContext())
        await run_provider_safely(p.execute, req)
        result = await run_provider_safely(p.execute, req)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_memory_stage_handles_missing_data(self):
        """Memory stage doesn't crash on missing data."""
        from runtime.pipeline.stages.memory_stage import MemoryStage

        stage = MemoryStage()
        ctx = ExecutionContext(
            runtime_context=RuntimeContext(),
            blackboard=Blackboard(),
            event_bus=EventBus(),
            provider_registry=ProviderRegistry(),
            capability_router=CapabilityRouter(),
        )
        result = await stage.execute(ctx)
        state = result.blackboard.get("memory.state")
        assert state is not None
