"""Mock providers for benchmarks.

Simulates realistic provider latencies and behaviors.
All mocks derive from the Provider ABC and return valid ProviderResult objects.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from runtime.models.provider import ProviderHealth, ProviderRequest, ProviderResult
from runtime.providers.base import Provider


class MockLatencyProvider(Provider):
    """Provider that simulates latency with configurable distribution.

    Useful for benchmark and load testing.
    """

    provider_id = "mock.latency"
    capability = "mock"
    config: dict[str, Any] = {}

    def __init__(
        self,
        *,
        base_latency_ms: float = 50.0,
        jitter_ms: float = 20.0,
        fail_rate: float = 0.0,
        fail_after: int = 0,
    ) -> None:
        self._base = base_latency_ms
        self._jitter = jitter_ms
        self._fail_rate = fail_rate
        self._fail_after = fail_after
        self._call_count = 0

    async def execute(self, _request: ProviderRequest) -> ProviderResult:
        self._call_count += 1

        # Simulate latency
        latency = max(0, self._base + random.uniform(-self._jitter, self._jitter))
        await asyncio.sleep(latency / 1000.0)

        # Failure simulation
        if self._fail_after > 0 and self._call_count > self._fail_after:
            return ProviderResult(success=False, error="simulated failure after limit")
        if random.random() < self._fail_rate:
            return ProviderResult(success=False, error="simulated random failure")

        return ProviderResult(
            success=True,
            data={"result": "ok", "call": self._call_count, "latency_ms": latency},
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True)

    @property
    def deterministic(self) -> bool:
        return False


class MockEchoProvider(Provider):
    """Provider that echoes request params with zero latency."""

    provider_id = "mock.echo"
    capability = "mock_echo"
    config: dict[str, Any] = {}

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(success=True, data=request.params)

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True)

    @property
    def deterministic(self) -> bool:
        return True


class MockSlowProvider(Provider):
    """Provider with a fixed high latency for timeout testing."""

    provider_id = "mock.slow"
    capability = "mock_slow"
    config: dict[str, Any] = {}

    def __init__(self, delay_ms: float = 5000.0) -> None:
        self._delay = delay_ms

    async def execute(self, _request: ProviderRequest) -> ProviderResult:
        await asyncio.sleep(self._delay / 1000.0)
        return ProviderResult(success=True, data={"result": "slow_ok"})

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True)

    @property
    def deterministic(self) -> bool:
        return True


class MockRetryProvider(Provider):
    """Provider that fails N times then succeeds."""

    provider_id = "mock.retry"
    capability = "mock_retry"
    config: dict[str, Any] = {}

    def __init__(self, fail_count: int = 2, latency_ms: float = 10.0) -> None:
        self._fail_count = fail_count
        self._latency = latency_ms
        self._attempts = 0

    async def execute(self, _request: ProviderRequest) -> ProviderResult:
        self._attempts += 1
        await asyncio.sleep(self._latency / 1000.0)
        if self._attempts <= self._fail_count:
            return ProviderResult(success=False, error=f"attempt {self._attempts} failed")
        return ProviderResult(
            success=True,
            data={"result": "ok", "attempts": self._attempts},
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True)

    @property
    def deterministic(self) -> bool:
        return True


def create_mock_registry():
    """Create a provider registry pre-populated with mock providers."""
    from runtime.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    providers = [
        MockLatencyProvider(base_latency_ms=10, jitter_ms=5),
        MockEchoProvider(),
        MockSlowProvider(delay_ms=500),
        MockRetryProvider(fail_count=1),
    ]
    for p in providers:
        registry.register(p.capability, p)
    return registry
