from __future__ import annotations

from typing import Any

from copilot.tools.base import BaseTool
from copilot.tools.disaster_tool import DisasterIntelligenceTool
from copilot.tools.forecast_tool import ForecastTool
from copilot.tools.rag_tool import RAGRetrieverTool
from copilot.tools.report_tool import ReportGeneratorTool
from copilot.tools.risk_tool import RiskAssessorTool
from copilot.tools.scenario_tool import ScenarioSimulatorTool
from copilot.tools.twin_tool import DigitalTwinTool


class ToolRegistry:
    def __init__(self, enabled_tools: list[str] | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()
        if enabled_tools is not None:
            self._filter_enabled(enabled_tools)

    def _register_defaults(self) -> None:
        defaults: list[BaseTool] = [
            ForecastTool(),
            DigitalTwinTool(),
            ScenarioSimulatorTool(),
            RiskAssessorTool(),
            RAGRetrieverTool(),
            ReportGeneratorTool(),
            DisasterIntelligenceTool(),
        ]
        for tool in defaults:
            meta = tool.describe()
            self._tools[meta["name"]] = tool

    def _filter_enabled(self, enabled: list[str]) -> None:
        self._tools = {name: tool for name, tool in self._tools.items() if name in enabled}

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ValueError(
                f"Tool '{name}' not found in registry. Available: {list(self._tools.keys())}"
            )
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.describe() for tool in self._tools.values()]

    def health_check_all(self) -> dict[str, tuple[bool, str]]:
        return {name: tool.health_check() for name, tool in self._tools.items()}

    def __contains__(self, name: str) -> bool:
        return name in self._tools
