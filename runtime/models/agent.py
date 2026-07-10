from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.models.runtime import RuntimeContext


@dataclass
class AgentParams:
    """Parameters passed to an agent for execution."""

    task: str
    params: dict[str, Any]
    context: RuntimeContext


@dataclass
class AgentResult:
    """Result from an agent execution."""

    success: bool
    data: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
