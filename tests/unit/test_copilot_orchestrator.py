"""Unit tests for copilot orchestrator."""

from copilot.models import IntentType
from copilot.workflows.orchestrator import CopilotOrchestrator


class TestCopilotOrchestrator:
    def setup_method(self):
        self.orchestrator = CopilotOrchestrator()

    def test_process_forecast_query(self):
        response = self.orchestrator.process("What is the weather in Karnataka?")
        assert response.answer
        assert response.intent == IntentType.FORECAST
        assert response.latency_ms > 0

    def test_process_greeting(self):
        response = self.orchestrator.process("Hello")
        assert response.intent == IntentType.GREETING
        assert "hello" in response.answer.lower()

    def test_process_risk_query(self):
        response = self.orchestrator.process("What is the flood risk in Karnataka?")
        assert response.intent == IntentType.RISK
        assert len(response.answer) > 0

    def test_process_unknown_query(self):
        response = self.orchestrator.process("xyzzy")
        assert response.intent == IntentType.UNKNOWN
        assert "not sure" in response.answer.lower()

    def test_intermediate_steps_returned(self):
        response = self.orchestrator.process("Forecast for Mysuru")
        assert len(response.intermediate_steps) > 0

    def test_citations_present_for_rag(self):
        response = self.orchestrator.process("Tell me about monsoon")
        assert response.intent == IntentType.RAG_QUERY
        if response.citations:
            assert len(response.citations) > 0

    def test_conversation_memory_maintained(self):
        cid = self.orchestrator.memory.create_conversation()
        self.orchestrator.process("Hello", conversation_id=cid)
        self.orchestrator.process("What is the weather?", conversation_id=cid)
        history = self.orchestrator.memory.get_history(cid)
        assert len(history) == 2

    def test_multiple_conversations(self):
        cid1 = self.orchestrator.memory.create_conversation()
        cid2 = self.orchestrator.memory.create_conversation()
        self.orchestrator.process("Hello", conversation_id=cid1)
        self.orchestrator.process("Forecast", conversation_id=cid2)
        convs = self.orchestrator.memory.list_conversations()
        assert len(convs) == 2
