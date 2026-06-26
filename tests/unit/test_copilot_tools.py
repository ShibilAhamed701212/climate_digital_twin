"""Unit tests for copilot tools."""

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
    def test_run_returns_forecast(self):
        tool = ForecastTool()
        result = tool.run(location="Karnataka", days=3)
        assert result["tool"] == "forecast_tool"
        assert len(result["forecast"]) == 3
        assert "max_temp" in result["forecast"][0]

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
    def test_run_returns_state(self):
        tool = DigitalTwinTool()
        result = tool.run(location="Karnataka")
        assert "state" in result
        assert result["state"]["location"] == "Karnataka"

    def test_validate(self):
        tool = DigitalTwinTool()
        valid, msg = tool.validate(location="Test")
        assert valid is True

    def test_health_check(self):
        tool = DigitalTwinTool()
        ok, msg = tool.health_check()
        assert ok is True


class TestScenarioTool:
    def test_run_temperature_scenario(self):
        tool = ScenarioSimulatorTool()
        result = tool.run(location="Karnataka", scenario_type="temperature", value=2.0)
        assert "result" in result
        assert "max_temp_delta" in result["result"]

    def test_validate_invalid_type(self):
        tool = ScenarioSimulatorTool()
        valid, msg = tool.validate(scenario_type="invalid_type")
        assert valid is False

    def test_validate_valid(self):
        tool = ScenarioSimulatorTool()
        valid, msg = tool.validate(scenario_type="rainfall", value=20.0)
        assert valid is True


class TestRiskTool:
    def test_run_returns_risk_scores(self):
        tool = RiskAssessorTool()
        result = tool.run(location="Karnataka")
        assert "risk_assessment" in result
        ra = result["risk_assessment"]
        assert all(k in ra for k in ["heat_risk", "flood_risk", "drought_risk", "composite_risk", "category"])

    def test_scores_in_range(self):
        tool = RiskAssessorTool()
        result = tool.run(location="Test")
        ra = result["risk_assessment"]
        assert 0 <= ra["heat_risk"] <= 100
        assert 0 <= ra["composite_risk"] <= 100


class TestRAGTool:
    def test_run_returns_results(self):
        tool = RAGRetrieverTool()
        result = tool.run(query="monsoon rainfall", top_k=3)
        assert len(result["results"]) == 3
        assert "source" in result["results"][0]

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
    def test_run_returns_report(self):
        tool = ReportGeneratorTool()
        result = tool.run(location="Karnataka", report_type="summary")
        assert "report" in result
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
