"""Unit tests for planning agent."""

from copilot.models import IntentResult, IntentType
from copilot.planner.planner import PlanningAgent
from copilot.tools.registry import ToolRegistry


class TestPlanningAgent:
    def setup_method(self):
        registry = ToolRegistry()
        self.planner = PlanningAgent(registry)

    def test_plan_forecast(self):
        intent = IntentResult(
            intent=IntentType.FORECAST,
            confidence=0.9,
            entities={"location": "Karnataka", "days": 3},
        )
        plan = self.planner.create_plan(intent)
        assert plan.intent == IntentType.FORECAST
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "forecast_tool"

    def test_plan_twin_state(self):
        intent = IntentResult(intent=IntentType.TWIN_STATE, confidence=0.8)
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "digital_twin_tool"

    def test_plan_scenario(self):
        intent = IntentResult(intent=IntentType.SCENARIO, confidence=0.85, sub_intent="temperature")
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "scenario_simulator"

    def test_plan_risk(self):
        intent = IntentResult(intent=IntentType.RISK, confidence=0.85)
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "risk_assessor"

    def test_plan_rag(self):
        intent = IntentResult(
            intent=IntentType.RAG_QUERY, confidence=0.75, raw_query="What causes monsoon?"
        )
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "rag_retriever"

    def test_plan_report(self):
        intent = IntentResult(
            intent=IntentType.REPORT, confidence=0.8, entities={"location": "Mysuru"}
        )
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 3
        assert plan.steps[0].tool_name == "forecast_tool"
        assert plan.steps[2].tool_name == "report_generator"

    def test_plan_greeting(self):
        intent = IntentResult(intent=IntentType.GREETING, confidence=0.9)
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 0

    def test_plan_unknown(self):
        intent = IntentResult(intent=IntentType.UNKNOWN, confidence=0.0)
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 0

    def test_low_confidence_returns_empty(self):
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.1)
        plan = self.planner.create_plan(intent)
        assert len(plan.steps) == 0
