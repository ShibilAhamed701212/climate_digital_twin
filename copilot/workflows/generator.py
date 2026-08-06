from __future__ import annotations

import json
import os
import re
from typing import Any

from copilot.llm.ollama_client import OllamaClient
from copilot.models import IntentResult, IntentType, Plan, ToolResult

PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


class ResponseGenerator:
    def __init__(self, llm_client: OllamaClient | None = None) -> None:
        self._llm = llm_client

    def generate(self, intent: IntentResult, plan: Plan, results: list[ToolResult]) -> str:
        if intent.intent == IntentType.UNKNOWN:
            return "I'm not sure how to help with that. Try asking about forecasts, risks, scenarios, or twin state."

        if intent.intent == IntentType.GREETING:
            return "Hello! I'm your Climate Copilot. Ask me about forecasts, climate risks, what-if scenarios, or the digital twin state."

        if not results:
            return "I couldn't find any relevant information. Please try rephrasing your query."

        failures = [r for r in results if not r.success]
        if failures:
            msgs = [f"  - {r.tool_name}: {r.error}" for r in failures]
            return "Some tools encountered errors:\n" + "\n".join(msgs)

        llm_response = self._try_llm(intent, plan, results)
        if llm_response is not None:
            cleaned = self._strip_reasoning(llm_response)
            if cleaned and len(cleaned) > 40:
                return cleaned

        generator = self._get_generator(intent.intent)
        return generator(intent, results)

    def _strip_reasoning(self, text: str) -> str:
        """Remove chain-of-thought leakage so only the final answer remains."""
        reasoning_markers = [
            "we are given",
            "the intent is",
            "tool results:",
            "steps:",
            "looking at the data",
            "we can say",
            "let's draft",
            "option:",
            "however, note",
            "paragraph ",
            "we must use only",
            "the rule says",
            "we don't have",
            "we have the tool name",
            "let me try",
        ]
        kept: list[str] = []
        for block in text.split("\n\n"):
            lower = block.strip().lower()
            if any(marker in lower for marker in reasoning_markers):
                continue
            if re.match(r"^\d+\.\s", block.strip()) and any(
                k in lower for k in ["we ", "the ", "looking", "trend", "must", "rule"]
            ):
                continue
            kept.append(block.strip())
        return "\n\n".join(b for b in kept if b).strip()

    def _try_llm(self, intent: IntentResult, _plan: Plan, results: list[ToolResult]) -> str | None:
        if self._llm is None:
            return None
        prompt_path = os.path.join(PROMPT_DIR, "generator.txt")
        results_data = []
        for r in results:
            entry = {"tool": r.tool_name, "success": r.success, "data": r.data}
            if r.error:
                entry["error"] = r.error
            results_data.append(entry)
        return self._llm.generate_with_prompt_file(
            prompt_path,
            query=intent.raw_query,
            intent=intent.intent.value,
            results=json.dumps(results_data, indent=2, default=str),
        )

    def _get_generator(self, intent: IntentType) -> Any:
        generators = {
            IntentType.FORECAST: self._format_forecast,
            IntentType.TWIN_STATE: self._format_twin_state,
            IntentType.SCENARIO: self._format_scenario,
            IntentType.RISK: self._format_risk,
            IntentType.RAG_QUERY: self._format_rag,
            IntentType.REPORT: self._format_report,
        }
        return generators.get(intent, self._format_default)

    def _get_citations(self, results: list[ToolResult]) -> list[str]:
        citations = []
        for r in results:
            if r.success and "source" in r.data.get("report", ""):
                citations.append("Source: Climate Copilot report")
            if r.success and "results" in r.data:
                for item in r.data["results"]:
                    if isinstance(item, dict) and "source" in item:
                        citations.append(f"Source: {item['source']}")
        return citations

    def _format_forecast(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and "forecast" in r.data:
                forecasts = r.data["forecast"]
                loc = r.data.get("location", "Karnataka")
                lines = [f"**{loc} — {len(forecasts)}-Day Forecast**", ""]
                for f in forecasts:
                    lines.append(
                        f"Day {f['day']} ({f['date']}): Max {f['max_temp']}°C, Min {f['min_temp']}°C, Rainfall {f['rainfall_mm']}mm, Humidity {f['humidity_pct']}%"
                    )
                return "\n".join(lines)
        return "Forecast data unavailable."

    def _format_twin_state(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and "state" in r.data:
                s = r.data["state"]
                return (
                    f"**Current Twin State — {s['location']}**\n\n"
                    f"- Max Temperature: {s['max_temp']}°C\n"
                    f"- Min Temperature: {s['min_temp']}°C\n"
                    f"- Rainfall: {s['rainfall_mm']}mm\n"
                    f"- Humidity: {s['humidity_pct']}%\n"
                    f"- Last Updated: {s['timestamp']}"
                )
        return "Twin state unavailable."

    def _format_scenario(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and "result" in r.data:
                sim = r.data["result"]
                lines = [f"**Scenario Simulation — {r.data.get('location', 'Karnataka')}**", ""]
                if "description" in sim:
                    lines.append(f"Description: {sim['description']}")
                if "max_temp_delta" in sim:
                    lines.append(f"Temperature Delta: {sim['max_temp_delta']:+.1f}°C")
                if "rainfall_delta_pct" in sim:
                    lines.append(f"Rainfall Delta: {sim['rainfall_delta_pct']:+.1f}%")
                if "monsoon_shift_days" in sim:
                    lines.append(f"Monsoon Shift: {sim['monsoon_shift_days']:+d} days")
                return "\n".join(lines)
        return "Scenario simulation unavailable."

    def _format_risk(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and "risk_assessment" in r.data:
                ra = r.data["risk_assessment"]
                if not isinstance(ra, dict) or "heat_risk" not in ra:
                    continue
                return (
                    f"**Climate Risk Assessment — {ra.get('location', 'Karnataka')}**\n\n"
                    f"- Heat Risk: {ra['heat_risk']}/100\n"
                    f"- Heavy Rain Risk: {ra.get('flood_risk', 0)}/100\n"
                    f"- Dryness Risk: {ra.get('drought_risk', 0)}/100\n"
                    f"- **Composite Risk: {ra.get('composite_risk', 0)}/100 ({ra.get('category', 'Unknown')})**"
                )
        return "Risk assessment unavailable."

    def _format_rag(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and "results" in r.data:
                items = r.data["results"]
                lines = ["**Knowledge Base Results**", ""]
                for i, item in enumerate(items, 1):
                    lines.append(
                        f"{i}. {item['content']} (Source: {item.get('source', 'unknown')}, Relevance: {item.get('score', 0):.2f})"
                    )
                return "\n".join(lines)
        return "No relevant knowledge found."

    def _format_report(self, _intent: IntentResult, results: list[ToolResult]) -> str:
        for r in results:
            if r.success and r.tool_name == "report_generator" and "report" in r.data:
                return f"**Generated Report**\n\n{r.data['report']}"
        # Fall back to combining available data
        parts = ["**Combined Climate Report**", ""]
        for r in results:
            if r.success:
                if "forecast" in r.data:
                    f = r.data["forecast"][0]
                    parts.append(
                        f"Forecast: Max {f['max_temp']}°C, Min {f['min_temp']}°C, Rain {f['rainfall_mm']}mm"
                    )
                if "risk_assessment" in r.data:
                    ra = r.data["risk_assessment"]
                    parts.append(f"Risk: Composite {ra['composite_risk']}/100 ({ra['category']})")
        return "\n".join(parts)

    def _format_default(self, intent: IntentResult, results: list[ToolResult]) -> str:
        return f"Processed your {intent.intent.value} request. Data retrieved from {len(results)} sources."
