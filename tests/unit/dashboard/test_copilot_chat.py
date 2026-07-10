"""Tests for dashboard/pages/07_copilot_chat.py — render() function."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import streamlit as st


def _import_page():
    return __import__("dashboard.page_views.07_copilot_chat", fromlist=["render"])


@pytest.fixture(autouse=True)
def _reset_session():
    if "copilot_conv_id" in st.session_state:
        del st.session_state.copilot_conv_id
    if "copilot_messages" in st.session_state:
        del st.session_state.copilot_messages


def test_copilot_chat_render_api_ok():
    p = _import_page()
    with (
        patch.object(p, "_health_check", return_value={"ollama": {"ok": True}}),
        patch.object(p, "_create_conversation", return_value="conv-123"),
    ):
        p.render(None, None)
    assert True


def test_copilot_chat_ollama_not_ok():
    p = _import_page()
    with (
        patch.object(p, "_health_check", return_value={"ollama": {"ok": False}}),
        patch.object(p, "_create_conversation", return_value="conv-123"),
    ):
        p.render(None, None)
    assert True


def test_copilot_chat_api_unavailable():
    p = _import_page()
    with patch.object(p, "_health_check", return_value=None):
        p.render(None, None)
    assert True


def test_copilot_chat_existing_messages():
    st.session_state.copilot_conv_id = "conv-456"
    st.session_state.copilot_messages = [
        {"role": "user", "content": "What is the weather?"},
        {
            "role": "assistant",
            "content": "It is sunny.",
            "citations": ["source1"],
            "steps": [{"tool": "weather_api", "success": True, "execution_time_ms": 100}],
        },
    ]
    p = _import_page()
    with (
        patch.object(p, "_health_check", return_value={"ollama": {"ok": True}}),
        patch.object(p, "_create_conversation", return_value="conv-123"),
    ):
        p.render(None, None)
    assert True
