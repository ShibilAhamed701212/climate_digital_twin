"""Unit tests for copilot FastAPI app (api/main.py)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from copilot.models import IntentType


@pytest.fixture(autouse=True)
def _mock_api():
    with patch("copilot.api.main.api") as mock_api:
        mock_api.health_check.return_value = {
            "status": "healthy",
            "tools": {"forecast_tool": "ok"},
            "conversations_active": 0,
        }
        mock_api.orchestrator.llm_client.health_check.return_value = (
            True,
            "Ollama running",
        )
        mock_ask_resp = MagicMock()
        mock_ask_resp.answer = "The weather is sunny"
        mock_ask_resp.citations = ["Source: IMD"]
        mock_ask_resp.intermediate_steps = []
        mock_ask_resp.latency_ms = 150.0
        mock_ask_resp.intent = IntentType.FORECAST
        mock_ask_resp.error = None
        mock_api.ask.return_value = mock_ask_resp
        mock_api.new_conversation.return_value = "conv-001"
        mock_api.get_history.return_value = [{"query": "hello", "response": "hi"}]
        mock_api.list_conversations.return_value = {"conv1": 3}
        yield mock_api


@pytest.fixture
def client():
    from copilot.api.main import app

    return TestClient(app)


class TestAppCreation:
    def test_app_title_and_version(self):
        from copilot.api.main import app

        assert app.title == "Climate Copilot API"
        assert app.version == "2.1.0"


class TestHealthEndpoint:
    def test_health_ok(self, client, _mock_api):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["ollama"]["ok"] is True

    def test_health_llm_failure(self, client, _mock_api):
        _mock_api.orchestrator.llm_client.health_check.side_effect = Exception("LLM crashed")
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ollama"]["ok"] is False

    def test_health_no_llm_client(self, client, _mock_api):
        del _mock_api.orchestrator.llm_client
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_tools_failure(self, client, _mock_api):
        _mock_api.health_check.side_effect = Exception("tools error")
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["tools"] == {}


class TestAskEndpoint:
    def test_ask_success(self, client, _mock_api):
        resp = client.post("/ask", json={"query": "weather?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "The weather is sunny"
        assert data["citations"] == ["Source: IMD"]

    def test_ask_error(self, client, _mock_api):
        err_resp = MagicMock()
        err_resp.error = "Something went wrong"
        _mock_api.ask.return_value = err_resp
        resp = client.post("/ask", json={"query": ""})
        assert resp.status_code == 400
        assert "Something went wrong" in resp.json()["detail"]

    def test_ask_with_conversation_id(self, client, _mock_api):
        resp = client.post("/ask", json={"query": "rain?", "conversation_id": "abc123"})
        assert resp.status_code == 200
        _mock_api.ask.assert_called_with("rain?", "abc123")


class TestConversationEndpoints:
    def test_create_conversation(self, client, _mock_api):
        resp = client.post("/conversation")
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == "conv-001"

    def test_get_history_success(self, client, _mock_api):
        resp = client.get("/conversation/abc123/history")
        assert resp.status_code == 200
        assert resp.json() == [{"query": "hello", "response": "hi"}]

    def test_get_history_not_found(self, client, _mock_api):
        _mock_api.get_history.side_effect = ValueError("Conversation not found")
        resp = client.get("/conversation/nonexistent/history")
        assert resp.status_code == 404

    def test_list_conversations(self, client, _mock_api):
        resp = client.get("/conversations")
        assert resp.status_code == 200
        assert resp.json() == {"conv1": 3}
