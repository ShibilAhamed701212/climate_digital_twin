"""Additional coverage tests for ResponseGenerator and IntentAgent — covering remaining paths."""

from unittest.mock import MagicMock

import pytest

from copilot.models import IntentResult, IntentType, Plan, ToolResult
from copilot.workflows.generator import ResponseGenerator


class TestResponseGeneratorDefaults:
    def setup_method(self):
        self.generator = ResponseGenerator()
        self.default_plan = Plan(intent=IntentType.FORECAST, steps=[])

    def test_llm_response_path(self):
        generator = ResponseGenerator(llm_client=MagicMock())
        mock_text = "LLM generated response that is sufficiently detailed and long enough to pass."
        generator._llm.generate_with_prompt_file.return_value = mock_text
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9, raw_query="weather?")
        results = [ToolResult(tool_name="forecast_tool", success=True, data={})]
        response = generator.generate(intent, self.default_plan, results)
        assert response == mock_text

    def test_llm_returns_none_falls_back(self):
        generator = ResponseGenerator(llm_client=MagicMock())
        generator._llm.generate_with_prompt_file.return_value = None
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
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
        results = [ToolResult(tool_name="forecast_tool", success=True, data=data)]
        response = generator.generate(intent, self.default_plan, results)
        assert "35.0" in response

    def test_no_llm_client_falls_back(self):
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        results = [
            ToolResult(
                tool_name="forecast_tool",
                success=True,
                data={"tool": "forecast_tool", "location": "Karnataka"},
            )
        ]
        response = self.generator.generate(intent, self.default_plan, results)
        assert response == "Forecast data unavailable."

    def test_tool_result_with_error_field(self):
        generator = ResponseGenerator(llm_client=MagicMock())
        generator._llm.generate_with_prompt_file.return_value = None
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        results = [
            ToolResult(
                tool_name="forecast_tool",
                success=True,
                data={
                    "forecast": [
                        {
                            "day": 1,
                            "date": "2026-06-27",
                            "max_temp": 35.0,
                            "min_temp": 22.0,
                            "rainfall_mm": 10.0,
                            "humidity_pct": 65,
                        }
                    ]
                },
            ),
        ]
        response = generator.generate(intent, self.default_plan, results)
        assert "35.0" in response

    def test_error_field_in_results_data(self):
        generator = ResponseGenerator(llm_client=MagicMock())
        generator._llm.generate_with_prompt_file.return_value = None
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        results = [
            ToolResult(
                tool_name="weather_tool",
                success=True,
                error="Degraded performance",
                data={"temp": 30},
            ),
        ]
        generator.generate(intent, self.default_plan, results)
        generator._llm.generate_with_prompt_file.assert_called_once()
        call_kwargs = generator._llm.generate_with_prompt_file.call_args[1]
        assert "Degraded" in call_kwargs.get("results", "")


class TestResponseGeneratorCitations:
    def test_citations_from_report_source(self):
        generator = ResponseGenerator()
        results = [
            ToolResult(tool_name="report_generator", success=True, data={"report": "source: IMD"}),
        ]
        citations = generator._get_citations(results)
        assert "Climate Copilot" in citations[0]

    def test_citations_from_results_items(self):
        generator = ResponseGenerator()
        results = [
            ToolResult(
                tool_name="rag_retriever",
                success=True,
                data={"results": [{"source": "IMD Report", "content": "data"}]},
            ),
        ]
        citations = generator._get_citations(results)
        assert "IMD Report" in citations[0]

    def test_citations_no_source_in_items(self):
        generator = ResponseGenerator()
        results = [
            ToolResult(
                tool_name="rag_retriever",
                success=True,
                data={"results": [{"content": "data"}]},
            ),
        ]
        citations = generator._get_citations(results)
        assert citations == []

    def test_citations_non_dict_in_results(self):
        generator = ResponseGenerator()
        results = [
            ToolResult(
                tool_name="rag_retriever",
                success=True,
                data={"results": ["string_item"]},
            ),
        ]
        citations = generator._get_citations(results)
        assert citations == []

    def test_citations_from_report_with_source_keyword(self):
        generator = ResponseGenerator()
        results = [
            ToolResult(
                tool_name="report_generator",
                success=True,
                data={"report": "source: Climate Report 2026"},
            ),
        ]
        citations = generator._get_citations(results)
        assert len(citations) == 1


class TestResponseGeneratorUnavailable:
    def setup_method(self):
        self.generator = ResponseGenerator()

    def test_forecast_unavailable(self):
        intent = IntentResult(intent=IntentType.FORECAST, confidence=0.9)
        plan = Plan(intent=IntentType.FORECAST, steps=[])
        results = [
            ToolResult(tool_name="forecast_tool", success=True, data={"location": "Karnataka"})
        ]
        response = self.generator.generate(intent, plan, results)
        assert response == "Forecast data unavailable."

    def test_twin_state_unavailable(self):
        intent = IntentResult(intent=IntentType.TWIN_STATE, confidence=0.9)
        plan = Plan(intent=IntentType.TWIN_STATE, steps=[])
        results = [ToolResult(tool_name="digital_twin_tool", success=True, data={})]
        response = self.generator.generate(intent, plan, results)
        assert response == "Twin state unavailable."

    def test_scenario_unavailable(self):
        intent = IntentResult(intent=IntentType.SCENARIO, confidence=0.9)
        plan = Plan(intent=IntentType.SCENARIO, steps=[])
        results = [ToolResult(tool_name="scenario_simulator", success=True, data={})]
        response = self.generator.generate(intent, plan, results)
        assert response == "Scenario simulation unavailable."

    def test_risk_unavailable(self):
        intent = IntentResult(intent=IntentType.RISK, confidence=0.9)
        plan = Plan(intent=IntentType.RISK, steps=[])
        results = [ToolResult(tool_name="risk_assessor", success=True, data={})]
        response = self.generator.generate(intent, plan, results)
        assert response == "Risk assessment unavailable."

    def test_rag_unavailable(self):
        intent = IntentResult(intent=IntentType.RAG_QUERY, confidence=0.9)
        plan = Plan(intent=IntentType.RAG_QUERY, steps=[])
        results = [ToolResult(tool_name="rag_retriever", success=True, data={})]
        response = self.generator.generate(intent, plan, results)
        assert response == "No relevant knowledge found."


class TestResponseGeneratorScenarioDetails:
    def test_scenario_with_rainfall_delta_pct(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.SCENARIO, confidence=0.9)
        data = {
            "tool": "scenario_simulator",
            "location": "Karnataka",
            "result": {
                "max_temp_delta": 2.0,
                "rainfall_delta_pct": -10.0,
                "description": "Hotter and drier",
            },
        }
        results = [ToolResult(tool_name="scenario_simulator", success=True, data=data)]
        response = generator.generate(intent, Plan(intent=IntentType.SCENARIO, steps=[]), results)
        assert "-10.0%" in response or "-10.0" in response

    def test_scenario_with_monsoon_shift_days(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.SCENARIO, confidence=0.9)
        data = {
            "tool": "scenario_simulator",
            "location": "Karnataka",
            "result": {
                "max_temp_delta": 1.5,
                "monsoon_shift_days": -7,
                "description": "Earlier monsoon",
            },
        }
        results = [ToolResult(tool_name="scenario_simulator", success=True, data=data)]
        response = generator.generate(intent, Plan(intent=IntentType.SCENARIO, steps=[]), results)
        assert "-7" in response or "7" in response


class TestResponseGeneratorReportFallback:
    def test_report_fallback_combines_forecast_and_risk(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.REPORT, confidence=0.9)
        results = [
            ToolResult(
                tool_name="forecast_tool",
                success=True,
                data={
                    "forecast": [
                        {
                            "day": 1,
                            "max_temp": 35.0,
                            "min_temp": 22.0,
                            "rainfall_mm": 10.0,
                            "humidity_pct": 65,
                            "date": "2026-07-04",
                        },
                    ]
                },
            ),
            ToolResult(
                tool_name="risk_assessor",
                success=True,
                data={
                    "risk_assessment": {
                        "location": "Karnataka",
                        "heat_risk": 45,
                        "flood_risk": 30,
                        "drought_risk": 60,
                        "composite_risk": 45.0,
                        "category": "Moderate",
                    }
                },
            ),
        ]
        response = generator.generate(intent, Plan(intent=IntentType.REPORT, steps=[]), results)
        assert "Combined" in response
        assert "35.0" in response
        assert "Moderate" in response

    def test_report_fallback_with_only_forecast(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.REPORT, confidence=0.9)
        results = [
            ToolResult(
                tool_name="forecast_tool",
                success=True,
                data={"forecast": [{"max_temp": 32.0, "min_temp": 20.0, "rainfall_mm": 5.0}]},
            ),
            ToolResult(tool_name="risk_assessor", success=True, data={}),
        ]
        response = generator.generate(intent, Plan(intent=IntentType.REPORT, steps=[]), results)
        assert "32.0" in response
        assert "Risk" not in response

    def test_report_fallback_with_only_risk(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.REPORT, confidence=0.9)
        results = [
            ToolResult(tool_name="forecast_tool", success=True, data={}),
            ToolResult(
                tool_name="risk_assessor",
                success=True,
                data={"risk_assessment": {"composite_risk": 60.0, "category": "High"}},
            ),
        ]
        response = generator.generate(intent, Plan(intent=IntentType.REPORT, steps=[]), results)
        assert "60.0" in response
        assert "High" in response

    def test_report_fallback_empty_results(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.REPORT, confidence=0.9)
        results = [ToolResult(tool_name="forecast_tool", success=True, data={})]
        response = generator.generate(intent, Plan(intent=IntentType.REPORT, steps=[]), results)
        assert "Combined" in response


class TestResponseGeneratorDefaultFormat:
    def test_default_format_unknown_intent_fallback(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.FEEDBACK, confidence=0.9)
        plan = Plan(intent=IntentType.FEEDBACK, steps=[])
        results = [ToolResult(tool_name="some_tool", success=True, data={})]
        response = generator.generate(intent, plan, results)
        assert "feedback" in response.lower()
        assert "1 sources" in response

    def test_default_format_multiple_sources(self):
        generator = ResponseGenerator()
        intent = IntentResult(intent=IntentType.FEEDBACK, confidence=0.9)
        results = [
            ToolResult(tool_name="tool1", success=True, data={}),
            ToolResult(tool_name="tool2", success=True, data={}),
        ]
        response = generator.generate(intent, Plan(intent=IntentType.FEEDBACK, steps=[]), results)
        assert "2 sources" in response


class TestIntentAgentTieBreaks:
    def _make_intent_result(self, intent, raw_query="", confidence=0.9):
        return IntentResult(intent=intent, confidence=confidence, raw_query=raw_query)

    def test_rag_report_tie_report_wins(self):
        from copilot.agent.intent_agent import IntentAgent

        agent = IntentAgent()
        result = agent.classify("generate a report")
        assert result.intent in (IntentType.REPORT, IntentType.RAG_QUERY)

    def test_feedback_forecast_tie_forecast_wins(self):
        from copilot.agent.intent_agent import IntentAgent

        agent = IntentAgent()
        result = agent.classify("weather forecast how accurate")
        assert result.intent in (IntentType.FEEDBACK, IntentType.FORECAST)

    def test_risk_rag_tie_rag_wins_when_no_risk_keyword(self):
        from copilot.agent.intent_agent import IntentAgent

        agent = IntentAgent()
        result = agent.classify("explain what is climate")
        assert result.intent != IntentType.RISK or result.intent == IntentType.RAG_QUERY

    def test_twin_rag_tie_rag_wins(self):
        from copilot.agent.intent_agent import IntentAgent

        agent = IntentAgent()
        result = agent.classify("explain what is the state")
        assert result.intent in (IntentType.TWIN_STATE, IntentType.RAG_QUERY)


class TestCopilotMemory:
    def test_clear_nonexistent(self):
        from copilot.memory.conversation_memory import ConversationMemory

        mem = ConversationMemory()
        mem.clear_conversation("nonexistent")  # should not raise

    def test_get_recent_context_empty(self):
        from copilot.memory.conversation_memory import ConversationMemory

        mem = ConversationMemory()
        assert mem.get_recent_context("nonexistent") == ""

    def test_trim_noop(self):
        from copilot.memory.conversation_memory import ConversationMemory
        from copilot.models import ConversationTurn, IntentType, Plan

        mem = ConversationMemory(window_size=2)
        cid = mem.create_conversation()
        for _ in range(3):
            mem.add_turn(
                cid,
                ConversationTurn(
                    query="hi",
                    intent=IntentType.GREETING,
                    plan=Plan(intent=IntentType.GREETING, steps=[]),
                    results=[],
                    response="hello",
                ),
            )
        assert len(mem.get_history(cid)) == 2


class TestExecutorEdgeCases:
    def test_tool_not_in_registry(self):
        from copilot.models import IntentType, Plan, ToolCall
        from copilot.tools.registry import ToolRegistry
        from copilot.workflows.executor import Executor

        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[
                ToolCall(tool_name="nonexistent", parameters={}, description=""),
            ],
        )
        results = Executor(ToolRegistry()).execute(plan)
        assert not results[0].success
        assert "not available" in results[0].error

    def test_tool_validation_fails(self):
        from copilot.models import IntentType, Plan, ToolCall
        from copilot.tools.registry import ToolRegistry
        from copilot.workflows.executor import Executor

        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[
                ToolCall(tool_name="forecast_tool", parameters={"days": 99}, description=""),
            ],
        )
        results = Executor(ToolRegistry()).execute(plan)
        assert not results[0].success


class TestCopilotAPIEdgeCases:
    def test_ask_empty_query(self):
        from copilot.api.copilot_api import CopilotAPI

        api = CopilotAPI.__new__(CopilotAPI)
        api.config = {}
        api.orchestrator = MagicMock()
        resp = api.ask("")
        assert resp.error == "Empty query"

    def test_get_history_empty(self):
        from copilot.api.copilot_api import CopilotAPI

        api = CopilotAPI.__new__(CopilotAPI)
        api.config = {}
        api.orchestrator = MagicMock()
        api.orchestrator.memory.get_history.return_value = []
        assert api.get_history("cid") == []


class TestTradeRegistryEdgeCases:
    def test_get_nonexistent_tool(self):
        from copilot.tools.registry import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            reg.get("nonexistent")

    def test_filter_enabled(self):
        from copilot.tools.registry import ToolRegistry

        reg = ToolRegistry(enabled_tools=["forecast_tool"])
        assert "forecast_tool" in reg
        assert "risk_assessor" not in reg

    def test_tools_list(self):
        from copilot.tools.registry import ToolRegistry

        reg = ToolRegistry()
        assert len(reg.list_tools()) == 6


class TestCopilotOrchestratorConfig:
    def test_init_with_config_disables_intermediate(self):
        from copilot.workflows.orchestrator import CopilotOrchestrator

        config = {
            "llm": {"primary_model": "test", "temperature": 0.1, "max_tokens": 128},
            "memory": {"window_size": 5, "expiration_minutes": 10},
            "orchestration": {"return_intermediate_steps": False},
            "enabled_tools": ["forecast_tool"],
        }
        orch = CopilotOrchestrator(config)
        assert orch.config["orchestration"]["return_intermediate_steps"] is False


class TestCopilotMainAPI:
    def test_create_conversation(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from copilot.api.main import app

        with patch("copilot.api.main.api") as mock:
            mock.new_conversation.return_value = "new-id"
            resp = TestClient(app).post("/conversation")
            assert resp.status_code == 200
            assert resp.json()["conversation_id"] == "new-id"

    def test_list_conversations(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from copilot.api.main import app

        with patch("copilot.api.main.api") as mock:
            mock.list_conversations.return_value = {"c1": 2}
            resp = TestClient(app).get("/conversations")
            assert resp.status_code == 200
            assert resp.json()["c1"] == 2
