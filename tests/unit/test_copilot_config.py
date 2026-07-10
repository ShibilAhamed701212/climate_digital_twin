"""Unit tests for copilot config loader."""

import os
import tempfile

import yaml


class TestCopilotConfig:
    def test_load_defaults(self):
        from copilot.config_loader import load_copilot_config

        config = load_copilot_config()
        assert "llm" in config
        assert config["llm"]["primary_model"] == "llama3.2:3b"
        assert config["llm"]["temperature"] == 0.1

    def test_load_custom_config(self):
        from copilot.config_loader import load_copilot_config

        custom = {
            "llm": {
                "primary_model": "custom-model",
                "temperature": 0.5,
                "max_tokens": 512,
                "context_window": 4096,
            },
            "memory": {"type": "test", "window_size": 5, "expiration_minutes": 30},
            "orchestration": {"max_iterations": 3, "return_intermediate_steps": False},
            "enabled_tools": ["forecast_tool"],
            "prompt_paths": {
                "intent_classification": "test.txt",
                "planning": "test.txt",
                "response_generation": "test.txt",
                "error_handling": "test.txt",
            },
            "performance_targets": {
                "simple_query_ms": 1000,
                "forecast_ms": 2000,
                "simulation_ms": 3000,
                "report_ms": 4000,
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(custom, f)
            tmp_path = f.name
        try:
            config = load_copilot_config(tmp_path)
            assert config["llm"]["primary_model"] == "custom-model"
            assert config["memory"]["window_size"] == 5
            assert config["orchestration"]["max_iterations"] == 3
            assert config["enabled_tools"] == ["forecast_tool"]
        finally:
            os.unlink(tmp_path)

    def test_enabled_tools_default(self):
        from copilot.config_loader import load_copilot_config

        config = load_copilot_config()
        assert "forecast_tool" in config["enabled_tools"]
        assert "rag_retriever" in config["enabled_tools"]
        assert len(config["enabled_tools"]) == 6
