from __future__ import annotations

from typing import Any

from copilot.models import IntentResult, IntentType, Plan, ToolCall
from copilot.tools.registry import ToolRegistry


class PlanningAgent:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def create_plan(self, intent: IntentResult) -> Plan:
        intent_type = intent.intent

        if intent_type == IntentType.UNKNOWN or intent.confidence < 0.3:
            return Plan(intent=intent_type, steps=[])

        planner = self._get_planner(intent_type)
        return planner(intent)

    def _get_planner(self, intent: IntentType) -> Any:
        planners = {
            IntentType.FORECAST: self._plan_forecast,
            IntentType.TWIN_STATE: self._plan_twin_state,
            IntentType.SCENARIO: self._plan_scenario,
            IntentType.RISK: self._plan_risk,
            IntentType.RAG_QUERY: self._plan_rag,
            IntentType.REPORT: self._plan_report,
            IntentType.GREETING: self._plan_greeting,
        }
        return planners.get(intent, self._plan_unknown)

    def _plan_forecast(self, intent: IntentResult) -> Plan:
        loc = intent.entities.get("location", "Karnataka")
        days = intent.entities.get("days", 3)
        return Plan(
            intent=IntentType.FORECAST,
            steps=[
                ToolCall(
                    tool_name="forecast_tool",
                    parameters={"location": loc, "days": days},
                    description=f"Get {days}-day forecast for {loc}",
                )
            ],
        )

    def _plan_twin_state(self, intent: IntentResult) -> Plan:
        loc = intent.entities.get("location", "Karnataka")
        return Plan(
            intent=IntentType.TWIN_STATE,
            steps=[
                ToolCall(
                    tool_name="digital_twin_tool",
                    parameters={"location": loc},
                    description=f"Get current twin state for {loc}",
                )
            ],
        )

    def _plan_scenario(self, intent: IntentResult) -> Plan:
        loc = intent.entities.get("location", "Karnataka")
        scenario_type = intent.sub_intent or "temperature"
        return Plan(
            intent=IntentType.SCENARIO,
            steps=[
                ToolCall(
                    tool_name="scenario_simulator",
                    parameters={"location": loc, "scenario_type": scenario_type, "value": 2.0},
                    description=f"Run {scenario_type} scenario for {loc}",
                )
            ],
        )

    def _plan_risk(self, intent: IntentResult) -> Plan:
        loc = intent.entities.get("location", "Karnataka")
        return Plan(
            intent=IntentType.RISK,
            steps=[
                ToolCall(
                    tool_name="risk_assessor",
                    parameters={"location": loc},
                    description=f"Assess climate risk for {loc}",
                )
            ],
        )

    def _plan_rag(self, intent: IntentResult) -> Plan:
        query = intent.raw_query
        return Plan(
            intent=IntentType.RAG_QUERY,
            steps=[
                ToolCall(
                    tool_name="rag_retriever",
                    parameters={"query": query, "top_k": 3},
                    description=f"Search knowledge base: {query}",
                )
            ],
        )

    def _plan_report(self, intent: IntentResult) -> Plan:
        loc = intent.entities.get("location", "Karnataka")
        return Plan(
            intent=IntentType.REPORT,
            steps=[
                ToolCall(
                    tool_name="forecast_tool",
                    parameters={"location": loc, "days": 3},
                    description=f"Get forecast for {loc} report",
                ),
                ToolCall(
                    tool_name="risk_assessor",
                    parameters={"location": loc},
                    description=f"Get risk data for {loc} report",
                ),
                ToolCall(
                    tool_name="report_generator",
                    parameters={"location": loc, "report_type": "summary"},
                    description=f"Generate report for {loc}",
                ),
            ],
        )

    def _plan_greeting(self, _intent: IntentResult) -> Plan:
        return Plan(intent=IntentType.GREETING, steps=[])

    def _plan_unknown(self, _intent: IntentResult) -> Plan:
        return Plan(intent=IntentType.UNKNOWN, steps=[])
