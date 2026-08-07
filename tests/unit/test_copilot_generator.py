"""Unit tests for response generator."""

from copilot.models import IntentResult, IntentType, Plan, ToolCall, ToolResult
from copilot.workflows.generator import ResponseGenerator


class TestResponseGenerator:
    def setup_method(self):
        self.generator = ResponseGenerator()

    def test_unknown_intent(self):
        intent = IntentResult(intent=IntentType.UNKNOWN, confidence=0.0)
        plan = Plan(intent=IntentType.UNKNOWN, steps=[])
        response = self.generator.generate(intent, plan, [])
        assert "not sure" in response.lower()

    def test_greeting(self):
        intent = IntentResult(intent=IntentType.GREETING, confidence=0.9)
        plan = Plan(intent=IntentType.GREETING, steps=[])
        response = self.generator.generate(intent, plan, [])
        assert "hello" in response.lower()

    def test_forecast_response(self):
        data = {
            "tool": "forecast_tool",
            "location": "Karnataka",
            "forecast": [
                {
                    "day": 1,
                    "date": "2026-06-27",
                    "max_temp": 35.0,
                    "min_temp": 22.0,
                    "rainfall_mm": 10.0,
                    "humidity_pct": 65,
                },
            ],
        }
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[ToolCall(tool_name="forecast_tool", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="forecast_tool", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "35.0" in response
        assert "Karnataka" in response

    def test_twin_state_response(self):
        data = {
            "tool": "digital_twin_tool",
            "location": "Mysuru",
            "state": {
                "location": "Mysuru",
                "max_temp": 32.0,
                "min_temp": 21.0,
                "rainfall_mm": 5.0,
                "humidity_pct": 70,
                "timestamp": "2026-06-26T12:00:00",
            },
        }
        intent = IntentResult(intent=IntentType.TWIN_STATE, confidence=0.8)
        plan = Plan(
            intent=IntentType.TWIN_STATE,
            steps=[ToolCall(tool_name="digital_twin_tool", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="digital_twin_tool", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "32.0" in response
        assert "Mysuru" in response

    def test_risk_response(self):
        data = {
            "tool": "risk_assessor",
            "location": "Karnataka",
            "risk_assessment": {
                "location": "Karnataka",
                "heat_risk": 45,
                "flood_risk": 30,
                "drought_risk": 60,
                "composite_risk": 45.0,
                "category": "Moderate",
            },
        }
        intent = IntentResult(intent=IntentType.RISK, confidence=0.85)
        plan = Plan(
            intent=IntentType.RISK,
            steps=[ToolCall(tool_name="risk_assessor", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="risk_assessor", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "Moderate" in response
        assert "45.0" in response

    def test_scenario_response(self):
        data = {
            "tool": "scenario_simulator",
            "location": "Karnataka",
            "scenario_type": "temperature",
            "value": 2.0,
            "result": {
                "max_temp_delta": 2.0,
                "rainfall_delta": 0,
                "description": "Temperature changes by 2.0°C",
            },
        }
        intent = IntentResult(intent=IntentType.SCENARIO, confidence=0.85)
        plan = Plan(
            intent=IntentType.SCENARIO,
            steps=[ToolCall(tool_name="scenario_simulator", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="scenario_simulator", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "+2.0" in response

    def test_rag_response(self):
        data = {
            "tool": "rag_retriever",
            "query": "monsoon",
            "results": [
                {
                    "source": "Climate Report",
                    "content": "Monsoon is caused by...",
                    "score": 0.95,
                    "category": "general",
                }
            ],
        }
        intent = IntentResult(intent=IntentType.RAG_QUERY, confidence=0.75)
        plan = Plan(
            intent=IntentType.RAG_QUERY,
            steps=[ToolCall(tool_name="rag_retriever", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="rag_retriever", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "Monsoon" in response
        assert "Climate Report" in response

    def test_report_response(self):
        data = {
            "tool": "report_generator",
            "report_type": "summary",
            "location": "Karnataka",
            "report": "# Climate Report\nSummary data",
        }
        intent = IntentResult(intent=IntentType.REPORT, confidence=0.8)
        plan = Plan(
            intent=IntentType.REPORT,
            steps=[ToolCall(tool_name="report_generator", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="report_generator", success=True, data=data)]
        response = self.generator.generate(intent, plan, results)
        assert "Climate Report" in response

    def test_no_results(self):
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        plan = Plan(intent=IntentType.FORECAST, steps=[])
        response = self.generator.generate(intent, plan, [])
        assert "couldn't find" in response.lower()

    def test_tool_failures(self):
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[ToolCall(tool_name="forecast_tool", parameters={}, description="")],
        )
        results = [ToolResult(tool_name="forecast_tool", success=False, error="API unavailable")]
        response = self.generator.generate(intent, plan, results)
        assert "error" in response.lower() or "API unavailable" in response
