from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    """A single step in a workflow DAG.

    Steps declare dependencies (depends_on) which the WorkflowEngine
    uses to determine parallel vs sequential execution.
    """

    id: str
    capability: str
    params: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    max_retries: int = 2
    on_failure: str = "abort"  # "abort", "skip", "fallback"


@dataclass
class WorkflowDefinition:
    """A declarative workflow DAG.

    The Runtime executes this graph without knowing its domain.
    Domain plugins register workflow definitions.
    """

    id: str
    name: str
    version: str
    description: str
    triggers: list[str]
    steps: list[WorkflowStep]
    timeout_ms: int = 60000
    metadata: dict[str, Any] = field(default_factory=dict)
