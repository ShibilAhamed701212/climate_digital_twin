from __future__ import annotations

from typing import Any

from copilot.config_loader import load_copilot_config
from copilot.models import CopilotResponse
from copilot.workflows.orchestrator import CopilotOrchestrator


class CopilotAPI:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_copilot_config()
        self.config = config
        self.orchestrator = CopilotOrchestrator(config)

    def ask(self, query: str, conversation_id: str | None = None) -> CopilotResponse:
        if not query or not query.strip():
            return CopilotResponse(answer="Please provide a valid query.", error="Empty query")
        return self.orchestrator.process(query.strip(), conversation_id)

    def new_conversation(self) -> str:
        return self.orchestrator.memory.create_conversation()

    def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        turns = self.orchestrator.memory.get_history(conversation_id)
        return [
            {
                "query": t.query,
                "intent": t.intent.value,
                "response": t.response,
                "latency_ms": t.latency_ms,
                "citations": t.citations,
            }
            for t in turns
        ]

    def list_conversations(self) -> dict[str, int]:
        return self.orchestrator.memory.list_conversations()

    def health_check(self) -> dict[str, Any]:
        tool_health = self.orchestrator.registry.health_check_all()
        return {
            "status": "healthy",
            "tools": {name: "ok" if ok else err for name, (ok, err) in tool_health.items()},
            "conversations_active": len(self.orchestrator.memory.list_conversations()),
        }
