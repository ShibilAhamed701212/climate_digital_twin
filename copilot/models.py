from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IntentType(StrEnum):
    FORECAST = "forecast"
    TWIN_STATE = "twin_state"
    SCENARIO = "scenario"
    RISK = "risk"
    RAG_QUERY = "rag_query"
    REPORT = "report"
    GREETING = "greeting"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentResult:
    intent: IntentType
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    raw_query: str = ""
    sub_intent: str | None = None


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    parameters: dict[str, Any]
    description: str = ""


@dataclass(frozen=True)
class Plan:
    intent: IntentType
    steps: list[ToolCall]
    required_context: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time_ms: float = 0.0


@dataclass(frozen=True)
class ConversationTurn:
    query: str
    intent: IntentType
    plan: Plan | None
    results: list[ToolResult]
    response: str
    latency_ms: float = 0.0
    citations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CopilotResponse:
    answer: str
    citations: list[str] = field(default_factory=list)
    intermediate_steps: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    intent: IntentType = IntentType.UNKNOWN
    error: str | None = None


@dataclass(frozen=True)
class CopilotContext:
    conversation_id: str
    history: list[ConversationTurn] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
