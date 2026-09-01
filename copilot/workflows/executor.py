from __future__ import annotations

import time

from copilot.models import Plan, ToolResult
from copilot.tools.registry import ToolRegistry


class Executor:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, plan: Plan) -> list[ToolResult]:
        results: list[ToolResult] = []
        for step in plan.steps:
            if step.tool_name not in self._registry:
                results.append(
                    ToolResult(
                        tool_name=step.tool_name,
                        success=False,
                        error=f"Tool '{step.tool_name}' not available",
                    )
                )
                continue
            tool = self._registry.get(step.tool_name)
            valid, msg = tool.validate(**step.parameters)
            if not valid:
                results.append(ToolResult(tool_name=step.tool_name, success=False, error=msg))
                continue
            start = time.perf_counter()
            try:
                data = tool.run(**step.parameters)
                elapsed = (time.perf_counter() - start) * 1000
                results.append(
                    ToolResult(
                        tool_name=step.tool_name,
                        success=True,
                        data=data,
                        execution_time_ms=round(elapsed, 2),
                    )
                )
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append(
                    ToolResult(
                        tool_name=step.tool_name,
                        success=False,
                        error=str(e),
                        execution_time_ms=round(elapsed, 2),
                    )
                )
        return results
