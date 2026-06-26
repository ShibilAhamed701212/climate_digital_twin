"""Unit tests for copilot API."""

from copilot.api.copilot_api import CopilotAPI


class TestCopilotAPI:
    def setup_method(self):
        self.api = CopilotAPI()

    def test_ask_returns_response(self):
        result = self.api.ask("What is the weather?")
        assert result.answer
        assert result.intent is not None

    def test_ask_empty_query(self):
        result = self.api.ask("")
        assert result.error == "Empty query"

    def test_new_conversation(self):
        cid = self.api.new_conversation()
        assert isinstance(cid, str)
        assert len(cid) == 8

    def test_get_history(self):
        cid = self.api.new_conversation()
        self.api.ask("Hello", conversation_id=cid)
        history = self.api.get_history(cid)
        assert len(history) == 1
        assert history[0]["query"] == "Hello"

    def test_list_conversations(self):
        self.api.new_conversation()
        self.api.new_conversation()
        convs = self.api.list_conversations()
        assert len(convs) >= 2

    def test_health_check(self):
        health = self.api.health_check()
        assert health["status"] == "healthy"
        assert "forecast_tool" in health["tools"]
