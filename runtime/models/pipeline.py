"""Execution context for pipelines, workflows, and background tasks.

ExecutionContext owns runtime state — not domain state.
Reusable by cognitive pipelines, autonomous workflows, scheduled jobs, and streaming pipelines.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.runtime import RuntimeContext
from runtime.providers.registry import ProviderRegistry

MAX_TRACE_ENTRIES = 500


@dataclass
class ExecutionContext:
    """Reusable execution context for pipelines, workflows, jobs, and streaming.

    Owns runtime state only — never domain concepts.
    Bounded trace: limited to MAX_TRACE_ENTRIES (500) entries.
    """

    runtime_context: RuntimeContext
    blackboard: Blackboard
    event_bus: EventBus
    provider_registry: ProviderRegistry
    capability_router: CapabilityRouter
    stage_outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    _trace: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_TRACE_ENTRIES))
    regenerate_count: int = 0

    @property
    def trace(self) -> list[dict[str, Any]]:
        return list(self._trace)

    def log_stage(self, stage: str, status: str, details: dict[str, Any] | None = None) -> None:
        self._trace.append(
            {
                "stage": stage,
                "status": status,
                "timestamp": time.time(),
                "elapsed_ms": self.runtime_context.elapsed_ms(),
                "details": details or {},
            }
        )

    def add_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    def add_error(self, stage: str, error: str) -> None:
        self.errors.append({"stage": stage, "error": error, "timestamp": time.time()})


class PipelineStage(ABC):
    """A single cognitive stage in a pipeline.

    Every stage implements lifecycle hooks.
    Runtime services (logging, tracing, metrics) use hooks rather than modifying stage logic.
    """

    name: str = ""
    description: str = ""
    dependencies: list[str] = []
    timeout_ms: int = 30000
    retry_count: int = 0

    async def before_execute(self, ctx: ExecutionContext) -> None:  # noqa: B027
        """Pre-execution hook. Override for setup."""
        pass

    @abstractmethod
    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        """Core execution logic. Must be implemented."""
        ...

    async def after_execute(self, ctx: ExecutionContext) -> None:  # noqa: B027
        """Post-execution hook. Override for cleanup."""
        pass

    async def on_error(self, ctx: ExecutionContext, error: Exception) -> ExecutionContext:
        """Error handler. Override for custom error recovery."""
        ctx.add_error(self.name, str(error))
        return ctx

    async def on_timeout(self, ctx: ExecutionContext) -> ExecutionContext:
        """Timeout handler. Override for custom timeout behavior."""
        ctx.add_error(self.name, f"Stage timed out after {self.timeout_ms}ms")
        return ctx


@dataclass
class CognitivePipeline:
    """Declarative pipeline definition.

    Stages can declare dependencies for DAG execution.
    The PipelineEngine resolves execution order.

    Future: stages with dependencies run in parallel where possible.
    """

    id: str
    triggers: list[str]
    stages: list[PipelineStage]
    timeout_ms: int = 60000
    metadata: dict[str, Any] = field(default_factory=dict)
