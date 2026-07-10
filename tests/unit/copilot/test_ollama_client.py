"""Unit tests for OllamaClient."""

from unittest.mock import MagicMock, patch

import httpx

from copilot.llm.ollama_client import OllamaClient


class TestOllamaClientInit:
    def test_default_values(self):
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"
        assert client.model == "llama3.2:3b"
        assert client.temperature == 0.1
        assert client.max_tokens == 1024
        assert client.timeout == 30.0

    def test_custom_values(self):
        client = OllamaClient(
            base_url="http://custom:11434",
            model="llama3",
            temperature=0.5,
            max_tokens=2048,
            timeout=60.0,
        )
        assert client.base_url == "http://custom:11434"
        assert client.model == "llama3"
        assert client.temperature == 0.5
        assert client.max_tokens == 2048
        assert client.timeout == 60.0

    def test_base_url_strips_trailing_slash(self):
        client = OllamaClient(base_url="http://localhost:11434/")
        assert client.base_url == "http://localhost:11434"


class TestOllamaClientGenerate:
    def setup_method(self):
        self.client = OllamaClient()
        self.client._client = MagicMock()

    def test_generate_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Hello, world!"}
        self.client._client.post.return_value = mock_resp
        result = self.client.generate("Say hello")
        assert result == "Hello, world!"

    def test_generate_with_system_prompt(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Answer"}
        self.client._client.post.return_value = mock_resp
        result = self.client.generate("Question", system_prompt="Be concise")
        assert result == "Answer"
        call_kwargs = self.client._client.post.call_args[1]
        assert call_kwargs["json"]["system"] == "Be concise"

    def test_generate_empty_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        self.client._client.post.return_value = mock_resp
        result = self.client.generate("Hi")
        assert result == ""

    def test_generate_whitespace_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "  hello  "}
        self.client._client.post.return_value = mock_resp
        result = self.client.generate("Hi")
        assert result == "hello"

    def test_generate_request_error(self):
        self.client._client.post.side_effect = httpx.RequestError("connection refused")
        with patch("copilot.llm.ollama_client.logger") as mock_log:
            result = self.client.generate("Hi")
            assert result is None
            mock_log.warning.assert_called_once()

    def test_generate_general_exception(self):
        self.client._client.post.side_effect = ValueError("unexpected")
        with patch("copilot.llm.ollama_client.logger") as mock_log:
            result = self.client.generate("Hi")
            assert result is None
            mock_log.warning.assert_called_once()

    def test_generate_timeout(self):
        self.client._client.post.side_effect = httpx.TimeoutException("timeout")
        result = self.client.generate("Hi")
        assert result is None


class TestGenerateWithPromptFile:
    def setup_method(self):
        self.client = OllamaClient()
        self.client._client = MagicMock()

    def test_prompt_file_success(self, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Answer about {topic}", encoding="utf-8")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Climate info"}
        self.client._client.post.return_value = mock_resp
        result = self.client.generate_with_prompt_file(
            str(prompt_file), system_prompt="Be brief", topic="climate"
        )
        assert result == "Climate info"

    def test_prompt_file_not_found(self):
        with patch("copilot.llm.ollama_client.logger") as mock_log:
            result = self.client.generate_with_prompt_file("/nonexistent/prompt.txt")
            assert result is None
            mock_log.warning.assert_called_once()


class TestHealthCheck:
    def setup_method(self):
        self.client = OllamaClient()

    def test_health_model_available(self):
        with patch.object(self.client, "_client") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": [{"name": "qwen3:8b"}, {"name": "llama3"}]}
            mock_http.get.return_value = mock_resp
            ok, msg = self.client.health_check()
            assert ok is True
            assert "available" in msg

    def test_health_model_not_available(self):
        with patch.object(self.client, "_client") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": [{"name": "llama3"}]}
            mock_http.get.return_value = mock_resp
            ok, msg = self.client.health_check()
            assert ok is True
            assert "not found" in msg
            assert "llama3" in msg

    def test_health_partial_model_match(self):
        with patch.object(self.client, "_client") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": [{"name": "qwen3:8b-instruct"}]}
            mock_http.get.return_value = mock_resp
            ok, msg = self.client.health_check()
            assert ok is True
            assert "available" in msg

    def test_health_connection_error(self):
        with patch.object(self.client, "_client") as mock_http:
            mock_http.get.side_effect = httpx.RequestError("connection refused")
            ok, msg = self.client.health_check()
            assert ok is False
            assert "unreachable" in msg

    def test_health_empty_models(self):
        with patch.object(self.client, "_client") as mock_http:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"models": []}
            mock_http.get.return_value = mock_resp
            ok, msg = self.client.health_check()
            assert ok is True
            assert "not found" in msg


class TestClose:
    def test_close(self):
        client = OllamaClient()
        with patch.object(client._client, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()
