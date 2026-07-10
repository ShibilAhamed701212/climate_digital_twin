"""Tests for reliability module (circuit breaker + retry)."""

from __future__ import annotations

import asyncio

import pytest

from runtime.reliability import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    call_with_circuit,
    retry,
)


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call(self):
        cb = CircuitBreaker("test")

        async def ok():
            return "ok"

        result = await cb.call(ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise ValueError("nope")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)

        # Circuit should be open
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_rejects_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)

        async def fail():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            await cb.call(fail)

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(fail)

    @pytest.mark.asyncio
    async def test_half_open_transition(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.01)

        async def fail():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_recovery_on_half_open_success(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.01)

        call_count = 0

        async def flip():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("fail first")
            return "ok"

        # First call fails → circuit opens
        with pytest.raises(ValueError):
            await cb.call(flip)

        # Wait for half-open
        await asyncio.sleep(0.02)

        # Probe succeeds → circuit closes
        result = await cb.call(flip)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_probe_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.01)

        async def fail():
            raise ValueError("still broken")

        # Trip
        with pytest.raises(ValueError):
            await cb.call(fail)

        # Wait for half-open
        await asyncio.sleep(0.02)

        # Probe fails → back to OPEN
        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        # Simulate failures
        cb._on_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_sync_function_call(self):
        cb = CircuitBreaker("sync_test")

        def sync_fn():
            return "sync"

        result = await cb.call(sync_fn)
        assert result == "sync"


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        call_count = 0

        @retry(max_attempts=3)
        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_after_failures(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        result = await fn()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fail")

        with pytest.raises(ValueError):
            await fn()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_sync_function(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("sync fail")

        with pytest.raises(ValueError):
            await fn()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_specific_exceptions(self):
        @retry(max_attempts=2, base_delay=0.01, retryable_exceptions=(ValueError,))
        async def fn():
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await fn()


class TestCallWithCircuit:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)

        async def ok():
            return "ok"

        result = await call_with_circuit(ok, circuit=cb)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.1)

        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        result = await call_with_circuit(flaky, circuit=cb)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)

        async def fail():
            raise ValueError("always fail")

        with pytest.raises(ValueError):
            await call_with_circuit(fail, circuit=cb)
        assert cb.state == CircuitState.OPEN
