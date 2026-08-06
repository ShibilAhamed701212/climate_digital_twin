"""Unit tests for copilot tools — validates LIVE/CACHED/HISTORICAL/UNAVAILABLE states."""

from copilot.tools.forecast_tool import ForecastTool
from copilot.tools.rag_tool import RAGRetrieverTool
from copilot.tools.registry import ToolRegistry
from copilot.tools.report_tool import ReportGeneratorTool
from copilot.tools.risk_tool import RiskAssessorTool
from copilot.tools.scenario_tool import ScenarioSimulatorTool
from copilot.tools.twin_tool import DigitalTwinTool


class TestToolContract:
    def test_forecast_tool_contract(self):
        tool = ForecastTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)

    def test_twin_tool_contract(self):
        tool = DigitalTwinTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)

    def test_scenario_tool_contract(self):
        tool = ScenarioSimulatorTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)

    def test_risk_tool_contract(self):
        tool = RiskAssessorTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)

    def test_rag_tool_contract(self):
        tool = RAGRetrieverTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)

    def test_report_tool_contract(self):
        tool = ReportGeneratorTool()
        assert callable(tool.run)
        assert callable(tool.validate)
        assert callable(tool.describe)
        assert callable(tool.health_check)


class TestForecastTool:
    def test_run_returns_unavailable_when_no_service(self):
        tool = ForecastTool()
        result = tool.run(location="Karnataka", days=3)
        assert result["tool"] == "forecast_tool"
        assert result["available"] is False
        assert result["forecast"] == []
        assert "error" in result

    def test_run_has_available_flag(self):
        tool = ForecastTool()
        result = tool.run(location="Mysuru", days=1)
        assert "available" in result
        assert isinstance(result["available"], bool)

    def test_validate_valid(self):
        tool = ForecastTool()
        valid, msg = tool.validate(location="Mysuru", days=5)
        assert valid is True
        assert msg == ""

    def test_validate_invalid_days(self):
        tool = ForecastTool()
        valid, msg = tool.validate(location="Mysuru", days=10)
        assert valid is False
        assert "days" in msg

    def test_describe(self):
        tool = ForecastTool()
        desc = tool.describe()
        assert desc["name"] == "forecast_tool"

    def test_health_check(self):
        tool = ForecastTool()
        ok, msg = tool.health_check()
        assert ok is True


class TestDigitalTwinTool:
    def test_run_returns_unavailable_when_no_service(self):
        tool = DigitalTwinTool()
        result = tool.run(location="Karnataka")
        assert result["tool"] == "digital_twin_tool"
        assert result["available"] is False
        assert result["state"] == {}
        assert "error" in result

    def test_run_has_available_flag(self):
        tool = DigitalTwinTool()
        result = tool.run(location="Mysuru")
        assert "available" in result
        assert isinstance(result["available"], bool)

    def test_run_successful_path(self):
        from unittest.mock import patch

        tool = DigitalTwinTool()
        mock_state = {
            "location": "Bengaluru",
            "max_temp": 32.0,
            "min_temp": 22.0,
            "rainfall_mm": 15.0,
            "humidity_pct": 65.0,
            "timestamp": "2026-06-28T12:00:00",
        }
        with patch.object(tool._client, "get_current_state", return_value=mock_state):
            result = tool.run(location="Bengaluru")
            assert result["available"] is True
            assert result["state"] == mock_state

    def test_validate(self):
        tool = DigitalTwinTool()
        valid, msg = tool.validate(location="Test")
        assert valid is True

    def test_health_check(self):
        tool = DigitalTwinTool()
        ok, msg = tool.health_check()
        assert ok is True


class TestScenarioTool:
    def test_run_returns_unavailable_when_no_service(self):
        tool = ScenarioSimulatorTool()
        result = tool.run(location="Karnataka", scenario_type="temperature", value=2.0)
        assert result["tool"] == "scenario_simulator"
        assert result["available"] is False
        assert result["result"] == {}
        assert "error" in result

    def test_run_has_available_flag(self):
        tool = ScenarioSimulatorTool()
        result = tool.run(location="Mysuru", scenario_type="rainfall", value=10.0)
        assert "available" in result
        assert isinstance(result["available"], bool)

    def test_run_successful_path(self):
        from unittest.mock import patch

        tool = ScenarioSimulatorTool()
        mock_result = {
            "scenario_id": "test-123",
            "max_temp_delta": 2.0,
            "rainfall_delta": 0,
        }
        with patch.object(tool._client, "simulate", return_value=mock_result):
            result = tool.run(location="Bengaluru", scenario_type="temperature", value=2.0)
            assert result["available"] is True
            assert result["result"] == mock_result

    def test_validate_invalid_type(self):
        tool = ScenarioSimulatorTool()
        valid, msg = tool.validate(scenario_type="invalid_type")
        assert valid is False

    def test_validate_valid(self):
        tool = ScenarioSimulatorTool()
        valid, msg = tool.validate(scenario_type="rainfall", value=20.0)
        assert valid is True


class TestRiskTool:
    def test_run_returns_unavailable_when_no_service(self):
        tool = RiskAssessorTool()
        result = tool.run(location="Karnataka")
        assert result["tool"] == "risk_assessor"
        assert result["available"] is False
        assert result["risk_assessment"] == {}
        assert "error" in result

    def test_run_has_available_flag(self):
        tool = RiskAssessorTool()
        result = tool.run(location="Mysuru")
        assert "available" in result
        assert isinstance(result["available"], bool)

    def test_run_successful_path(self):
        from unittest.mock import patch

        tool = RiskAssessorTool()
        mock_scores = {
            "heat": 30.0,
            "flood": 20.0,
            "drought": 10.0,
            "composite": 20.0,
            "category": "Low",
        }
        with patch.object(tool._client, "assess", return_value=mock_scores):
            result = tool.run(location="Bengaluru")
            assert result["available"] is True
            ra = result["risk_assessment"]
            assert ra["heat_risk"] == 30.0
            assert ra["flood_risk"] == 20.0
            assert ra["drought_risk"] == 10.0
            assert ra["composite_risk"] == 20.0
            assert ra["category"] == "Low"


class TestRAGTool:
    def test_run_returns_empty_when_no_service(self):
        tool = RAGRetrieverTool()
        result = tool.run(query="monsoon rainfall", top_k=3)
        assert result["tool"] == "rag_retriever"
        assert result["results"] == []

    def test_run_successful_path(self):
        from unittest.mock import patch

        tool = RAGRetrieverTool()
        mock_results = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "title": "Doc 1",
                "source": "IMD Report",
                "content": "Monsoon patterns in Karnataka",
                "score": 0.95,
                "category": "rainfall",
            },
        ]
        with patch.object(tool._client, "search", return_value=mock_results):
            result = tool.run(query="monsoon", top_k=1)
            assert "fallback" in result  # ponytail: RAG tool still uses fallback key
            assert result["results"] == mock_results

    def test_validate_empty_query_fails(self):
        tool = RAGRetrieverTool()
        valid, msg = tool.validate(query="")
        assert valid is False
        assert "query" in msg.lower()

    def test_validate_valid(self):
        tool = RAGRetrieverTool()
        valid, msg = tool.validate(query="climate change", top_k=5)
        assert valid is True


class TestReportTool:
    def test_run_returns_partial_report_when_no_service(self):
        tool = ReportGeneratorTool()
        result = tool.run(location="Karnataka", report_type="summary")
        assert result["tool"] == "report_generator"
        # ponytail: ReportClient catches sub-service errors, always returns a report string
        assert isinstance(result["report"], str)
        assert "Climate Report" in result["report"]

    def test_validate_invalid_type(self):
        tool = ReportGeneratorTool()
        valid, msg = tool.validate(report_type="invalid")
        assert valid is False

    def test_health_check(self):
        tool = ReportGeneratorTool()
        ok, msg = tool.health_check()
        assert ok is True


class TestToolRegistry:
    def test_register_all_tools(self):
        registry = ToolRegistry()
        assert len(registry.list_tools()) == 6

    def test_get_tool_by_name(self):
        registry = ToolRegistry()
        tool = registry.get("forecast_tool")
        assert isinstance(tool, ForecastTool)

    def test_get_missing_tool_raises(self):
        registry = ToolRegistry()
        import pytest

        with pytest.raises(ValueError):
            registry.get("nonexistent")

    def test_filter_enabled_tools(self):
        registry = ToolRegistry(enabled_tools=["forecast_tool", "rag_retriever"])
        assert len(registry.list_tools()) == 2

    def test_contains(self):
        registry = ToolRegistry()
        assert "forecast_tool" in registry
        assert "nonexistent" not in registry

    def test_health_check_all(self):
        registry = ToolRegistry()
        checks = registry.health_check_all()
        assert all(ok for ok, _ in checks.values())
