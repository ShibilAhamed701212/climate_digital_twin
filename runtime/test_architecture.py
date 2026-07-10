"""Architectural tests verifying Runtime contains no domain-specific logic."""

import ast
import os

import pytest

RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))

FORBIDDEN_TERMS = [
    "climate",
    "weather",
    "rainfall",
    "temperature",
    "humidity",
    "twin",
    "forecast",
    "scenario",
    "risk",
    "karnataka",
    "bengaluru",
    "mysore",
    "bangalore",
    "isro",
    "imd",
    "nasa",
    "digital twin",
    "streamlit",
    "ollama",
]


def get_python_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith(".py") and not f.startswith("test_"):
                files.append(os.path.join(root, f))
    return files


class TestNoDomainLeaks:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_domain_terms(self, term):
        files = get_python_files(RUNTIME_DIR)
        for filepath in files:
            with open(filepath) as f:
                for i, line in enumerate(f, 1):
                    if term.lower() in line.lower() and "FORBIDDEN_TERMS" not in line:
                        pytest.fail(
                            f"{os.path.relpath(filepath)}:{i}: contains '{term}'"
                        )


class TestNoDomainImports:
    def test_no_external_imports(self):
        forbidden_imports = [
            "copilot",
            "climate",
            "streamlit",
            "ollama",
            "fastapi",
            "uvicorn",
        ]
        for filepath in get_python_files(RUNTIME_DIR):
            with open(filepath) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for fi in forbidden_imports:
                            if alias.name.startswith(fi):
                                pytest.fail(
                                    f"{os.path.relpath(filepath)} imports '{alias.name}'"
                                )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for fi in forbidden_imports:
                        if node.module.startswith(fi):
                            pytest.fail(
                                f"{os.path.relpath(filepath)} imports '{node.module}'"
                            )


class TestInterfaces:
    def test_blackboard(self):
        from runtime.blackboard import Blackboard

        bb = Blackboard()
        assert all(
            hasattr(bb, m) for m in ["publish", "get", "watch", "history", "query"]
        )

    def test_event_bus(self):
        from runtime.event_bus import EventBus

        assert all(hasattr(EventBus(), m) for m in ["publish", "subscribe", "history"])

    def test_provider_abc(self):
        from runtime.providers.base import Provider

        assert hasattr(Provider, "execute")
        assert hasattr(Provider, "health")

    def test_plugin_abc(self):
        from runtime.plugins.base import Plugin

        for m in [
            "register_capabilities",
            "register_agents",
            "register_providers",
            "register_events",
            "register_workflows",
            "register_configuration",
        ]:
            assert hasattr(Plugin, m)
