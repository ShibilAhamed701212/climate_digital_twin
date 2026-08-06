from __future__ import annotations

import os
from typing import Any

import yaml

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "copilot.yaml")
_cache: dict[str, Any] | None = None


def load_copilot_config(path: str | None = None) -> dict[str, Any]:
    global _cache
    config_path = path or _CONFIG_PATH
    if path is not None:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        return _defaults()
    if _cache is not None:
        return _cache
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            _cache = yaml.safe_load(f)
    else:
        _cache = _defaults()
    return _cache


def _defaults() -> dict[str, Any]:
    return {
        "llm": {
            "primary_model": "qwen3:4b",
            "temperature": 0.1,
            "max_tokens": 1024,
            "context_window": 8192,
        },
        "memory": {
            "type": "conversation_buffer_window",
            "window_size": 10,
            "expiration_minutes": 60,
        },
        "orchestration": {"max_iterations": 5, "return_intermediate_steps": True},
        "enabled_tools": [
            "forecast_tool",
            "digital_twin_tool",
            "scenario_simulator",
            "risk_assessor",
            "rag_retriever",
            "report_generator",
        ],
        "prompt_paths": {
            "intent_classification": "copilot/prompts/intent.txt",
            "planning": "copilot/prompts/planner.txt",
            "response_generation": "copilot/prompts/generator.txt",
            "error_handling": "copilot/prompts/error.txt",
        },
        "performance_targets": {
            "simple_query_ms": 2000,
            "forecast_ms": 5000,
            "simulation_ms": 8000,
            "report_ms": 10000,
        },
    }
