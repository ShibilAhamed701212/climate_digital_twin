from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen:4b"
DEFAULT_TIMEOUT = 30.0


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str | None:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = self._client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except httpx.RequestError as e:
            logger.warning("Ollama request failed: %s", e)
            return None
        except Exception as e:
            logger.warning("Ollama error: %s", e)
            return None

    def generate_with_prompt_file(
        self,
        prompt_path: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str | None:
        try:
            with open(prompt_path, encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            logger.warning("Prompt file not found: %s", prompt_path)
            return None
        prompt = template.format(**kwargs)
        return self.generate(prompt, system_prompt)

    def health_check(self) -> tuple[bool, str]:
        try:
            resp = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            available = [m["name"] for m in models]
            if self.model in available or any(self.model in m for m in available):
                return True, f"Ollama running, model {self.model} available"
            return True, f"Ollama running (model {self.model} not found, available: {', '.join(available)})"
        except httpx.RequestError as e:
            return False, f"Ollama unreachable: {e}"

    def close(self) -> None:
        self._client.close()
