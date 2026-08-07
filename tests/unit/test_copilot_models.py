"""Unit tests for copilot models."""

from copilot.models import (
    ConversationTurn,
    CopilotContext,
    CopilotResponse,
    IntentResult,
    IntentType,
    Plan,
    ToolCall,
    ToolResult,
)


class TestIntentType:
    def test_enum_values(self):
        assert IntentType.FORECAST.value == "forecast"
        assert IntentType.TWIN_STATE.value == "twin_state"
        assert IntentType.UNKNOWN.value == "unknown"

    def test_all_values_unique(self):
        values = [e.value for e in IntentType]
        assert len(values) == len(set(values))


class TestIntentResult:
    def test_create(self):
        r = IntentResult(intent=IntentType.FORECAST, confidence=0.85, raw_query="weather")
        assert r.intent == IntentType.FORECAST
        assert r.confidence == 0.85

    def test_default_entities(self):
        r = IntentResult(intent=IntentType.UNKNOWN, confidence=0.0)
        assert r.entities == {}


class TestToolCall:
    def test_create(self):
        tc = ToolCall(tool_name="forecast_tool", parameters={"location": "Karnataka"})
        assert tc.tool_name == "forecast_tool"


class TestPlan:
    def test_create_with_steps(self):
        tc = ToolCall(
            tool_name="forecast_tool",
            parameters={"location": "Karnataka", "days": 3},
            description="test",
        )
        p = Plan(intent=IntentType.FORECAST, steps=[tc])
        assert len(p.steps) == 1

    def test_empty_steps(self):
        p = Plan(intent=IntentType.GREETING, steps=[])
        assert p.steps == []


class TestToolResult:
    def test_success(self):
        r = ToolResult(tool_name="forecast_tool", success=True, data={"key": "val"})
        assert r.success is True
        assert r.data["key"] == "val"

    def test_failure(self):
        r = ToolResult(tool_name="forecast_tool", success=False, error="fail")
        assert r.success is False
        assert r.error == "fail"

    def test_defaults(self):
        r = ToolResult(tool_name="test", success=True)
        assert r.data == {}
        assert r.error is None
        assert r.execution_time_ms == 0.0


class TestConversationTurn:
    def test_create(self):
        ct = ConversationTurn(
            query="hello",
            intent=IntentType.GREETING,
            plan=Plan(intent=IntentType.GREETING, steps=[]),
            results=[],
            response="Hi there",
        )
        assert ct.query == "hello"
        assert ct.response == "Hi there"

    def test_default_citations(self):
        ct = ConversationTurn(
            query="q", intent=IntentType.UNKNOWN, plan=None, results=[], response="r"
        )
        assert ct.citations == []


class TestCopilotResponse:
    def test_create(self):
        r = CopilotResponse(answer="Test answer")
        assert r.answer == "Test answer"

    def test_defaults(self):
        r = CopilotResponse(answer="")
        assert r.citations == []
        assert r.intermediate_steps == []
        assert r.latency_ms == 0.0
        assert r.intent == IntentType.UNKNOWN
        assert r.error is None


class TestCopilotContext:
    def test_create(self):
        ctx = CopilotContext(conversation_id="abc123")
        assert ctx.conversation_id == "abc123"
        assert ctx.history == []
