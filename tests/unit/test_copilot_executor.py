"""Unit tests for executor."""

from copilot.models import IntentType, Plan, ToolCall
from copilot.tools.registry import ToolRegistry
from copilot.workflows.executor import Executor


class TestExecutor:
    def setup_method(self):
        registry = ToolRegistry()
        self.executor = Executor(registry)

    def test_execute_forecast_plan(self):
        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[ToolCall(tool_name="forecast_tool", parameters={"location": "Karnataka", "days": 3}, description="test")],
        )
        results = self.executor.execute(plan)
        assert len(results) == 1
        assert results[0].success is True
        assert "forecast" in results[0].data

    def test_execute_missing_tool(self):
        plan = Plan(
            intent=IntentType.UNKNOWN,
            steps=[ToolCall(tool_name="nonexistent_tool", parameters={}, description="test")],
        )
        results = self.executor.execute(plan)
        assert len(results) == 1
        assert results[0].success is False
        assert "not available" in (results[0].error or "")

    def test_execute_invalid_parameters(self):
        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[ToolCall(tool_name="forecast_tool", parameters={"days": 100}, description="test")],
        )
        results = self.executor.execute(plan)
        assert len(results) == 1
        assert results[0].success is False

    def test_execute_empty_plan(self):
        plan = Plan(intent=IntentType.GREETING, steps=[])
        results = self.executor.execute(plan)
        assert results == []

    def test_execution_time_tracked(self):
        plan = Plan(
            intent=IntentType.FORECAST,
            steps=[ToolCall(tool_name="forecast_tool", parameters={"location": "Karnataka", "days": 1}, description="test")],
        )
        results = self.executor.execute(plan)
        assert results[0].execution_time_ms > 0

    def test_execute_multiple_tools(self):
        plan = Plan(
            intent=IntentType.REPORT,
            steps=[
                ToolCall(tool_name="forecast_tool", parameters={"location": "Karnataka", "days": 1}),
                ToolCall(tool_name="risk_assessor", parameters={"location": "Karnataka"}),
            ],
        )
        results = self.executor.execute(plan)
        assert len(results) == 2
        assert all(r.success for r in results)
