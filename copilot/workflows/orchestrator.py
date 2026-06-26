from __future__ import annotations

import time
from typing import Any

from copilot.agent.intent_agent import IntentAgent
from copilot.config_loader import load_copilot_config
from copilot.memory.conversation_memory import ConversationMemory
from copilot.models import ConversationTurn, CopilotResponse
from copilot.planner.planner import PlanningAgent
from copilot.tools.registry import ToolRegistry
from copilot.workflows.executor import Executor
from copilot.workflows.generator import ResponseGenerator


class CopilotOrchestrator:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_copilot_config()
        self.config = config
        enabled = config.get("enabled_tools")
        self.registry = ToolRegistry(enabled_tools=enabled)
        self.intent_agent = IntentAgent()
        self.planner = PlanningAgent(self.registry)
        self.executor = Executor(self.registry)
        self.generator = ResponseGenerator()
        mem_cfg = config.get("memory", {})
        self.memory = ConversationMemory(
            window_size=mem_cfg.get("window_size", 10),
            expiration_minutes=mem_cfg.get("expiration_minutes", 60),
        )

    def process(self, query: str, conversation_id: str | None = None) -> CopilotResponse:
        start = time.perf_counter()
        if conversation_id is None or conversation_id not in self.memory._conversations:
            conversation_id = self.memory.create_conversation()

        intent = self.intent_agent.classify(query)
        plan = self.planner.create_plan(intent)
        results = self.executor.execute(plan)
        response_text = self.generator.generate(intent, plan, results)
        elapsed = (time.perf_counter() - start) * 1000

        citations = self.generator._get_citations(results)
        turn = ConversationTurn(
            query=query,
            intent=intent.intent,
            plan=plan,
            results=results,
            response=response_text,
            latency_ms=round(elapsed, 2),
            citations=citations,
        )
        self.memory.add_turn(conversation_id, turn)

        intermediate = []
        if self.config.get("orchestration", {}).get("return_intermediate_steps", True):
            for r in results:
                intermediate.append({
                    "tool": r.tool_name,
                    "success": r.success,
                    "error": r.error,
                    "execution_time_ms": r.execution_time_ms,
                })

        return CopilotResponse(
            answer=response_text,
            citations=citations,
            intermediate_steps=intermediate,
            latency_ms=round(elapsed, 2),
            intent=intent.intent,
        )
