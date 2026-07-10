"""Shared fixtures and helpers for Runtime tests."""

from __future__ import annotations

import pytest

from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.pipeline import ExecutionContext
from runtime.models.runtime import RuntimeContext
from runtime.providers.registry import ProviderRegistry


@pytest.fixture
def ctx() -> ExecutionContext:
    """Standard ExecutionContext for Runtime pipeline stage tests."""
    return ExecutionContext(
        runtime_context=RuntimeContext(),
        blackboard=Blackboard(),
        event_bus=EventBus(),
        provider_registry=ProviderRegistry(),
        capability_router=CapabilityRouter(),
    )


def make_context() -> ExecutionContext:
    """Create a fresh ExecutionContext inline (for tests that need it without fixture)."""
    return ExecutionContext(
        runtime_context=RuntimeContext(),
        blackboard=Blackboard(),
        event_bus=EventBus(),
        provider_registry=ProviderRegistry(),
        capability_router=CapabilityRouter(),
    )
