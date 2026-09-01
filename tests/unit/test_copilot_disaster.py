from __future__ import annotations

from copilot.models import IntentResult, IntentType
from copilot.planner.planner import PlanningAgent
from copilot.tools.disaster_tool import DisasterIntelligenceTool
from copilot.tools.registry import ToolRegistry
from copilot.workflows.generator import ResponseGenerator


def test_registry_includes_disaster() -> None:
    registry = ToolRegistry()
    assert len(registry.list_tools()) == 7
    assert "disaster_intelligence" in registry


def test_disaster_tool_unavailable() -> None:
    tool = DisasterIntelligenceTool()
    result = tool.run(location="KA-HAS-001", action="summary")
    assert result["available"] is False
    assert "error" in result


def test_plan_disaster() -> None:
    planner = PlanningAgent(ToolRegistry())
    plan = planner.create_plan(
        IntentResult(
            intent=IntentType.DISASTER, confidence=0.9, entities={"location": "KA-HAS-001"}
        )
    )
    assert plan.steps[0].tool_name == "disaster_intelligence"


def test_format_disaster_unavailable() -> None:
    from copilot.models import Plan, ToolResult

    gen = ResponseGenerator(llm_client=None)
    text = gen.generate(
        IntentResult(intent=IntentType.DISASTER, confidence=0.9),
        Plan(intent=IntentType.DISASTER, steps=[]),
        [
            ToolResult(
                tool_name="disaster_intelligence",
                success=True,
                data={"available": False, "error": "No verified disaster assessment is available."},
            )
        ],
    )
    assert "No verified disaster assessment" in text


def test_format_disaster_includes_provenance() -> None:
    from copilot.models import Plan, ToolResult

    gen = ResponseGenerator(llm_client=None)
    text = gen.generate(
        IntentResult(intent=IntentType.DISASTER, confidence=0.9),
        Plan(intent=IntentType.DISASTER, steps=[]),
        [
            ToolResult(
                tool_name="disaster_intelligence",
                success=True,
                data={
                    "available": True,
                    "location": "KA-HAS-001",
                    "overlay": {
                        "assessment_id": "a1",
                        "authenticity": "USER_UPLOAD",
                        "model_cards": {"flood": "s1-threshold-v0"},
                        "kpis": {"flood_area_km2": 1.2},
                        "quality_flags": ["s1_only"],
                    },
                },
            )
        ],
    )
    assert "Authenticity: USER_UPLOAD" in text
    assert "s1_only" in text
    assert "GET /disaster/twin/KA-HAS-001" in text
    assert "Processing:" in text
    assert "confidence_type" in text
