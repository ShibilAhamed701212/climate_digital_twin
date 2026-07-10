"""Page 7: AI Copilot Chat — conversational climate assistant."""  # noqa: N999

from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from dashboard.config.config import COPILOT_API_URL

PAGE_TITLE = "AI Climate Copilot"
PAGE_ICON = "🤖"


def _get_api_url() -> str:
    return COPILOT_API_URL.rstrip("/")


def _ask_copilot(query: str, conversation_id: str | None = None) -> dict[str, Any] | None:
    try:
        resp = requests.post(
            f"{_get_api_url()}/ask",
            json={"query": query, "conversation_id": conversation_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def _create_conversation() -> str | None:
    try:
        resp = requests.post(f"{_get_api_url()}/conversation", timeout=5)
        resp.raise_for_status()
        return resp.json().get("conversation_id")
    except requests.RequestException:
        return None


def _health_check() -> dict[str, Any] | None:
    try:
        resp = requests.get(f"{_get_api_url()}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def render(_api: Any = None, _filters: dict[str, Any] | None = None) -> None:
    st.header(f"{PAGE_ICON} {PAGE_TITLE}")
    st.caption(
        "Chat with the AI-powered Climate Copilot about forecasts, risks, scenarios, and more"
    )

    health = _health_check()
    if health is None:
        st.warning(
            "Copilot API unavailable. Start the copilot service to enable AI-powered responses."
        )
        return
    ollama_ok = health.get("ollama", {}).get("ok", False)
    if not ollama_ok:
        st.info("Ollama model not detected. Copilot will use rule-based responses.")

    if "copilot_conv_id" not in st.session_state:
        conv_id = _create_conversation()
        st.session_state.copilot_conv_id = conv_id or "demo"
        st.session_state.copilot_messages = []

    for msg in st.session_state.copilot_messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])
            if role == "assistant" and msg.get("citations"):
                with st.expander("Sources", expanded=False):
                    for c in msg["citations"]:
                        st.write(f"- {c}")
            if role == "assistant" and msg.get("steps"):
                with st.expander("Tool steps", expanded=False):
                    for s in msg["steps"]:
                        status = "✅" if s.get("success") else "❌"
                        st.write(
                            f"{status} {s.get('tool', '?')} ({s.get('execution_time_ms', 0):.0f}ms)"
                        )

    user_query = st.chat_input("Ask about climate, forecasts, risks, or scenarios...")
    if user_query:
        with st.chat_message("user"):
            st.markdown(user_query)

        st.session_state.copilot_messages.append({"role": "user", "content": user_query})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = _ask_copilot(user_query, st.session_state.copilot_conv_id)

            if result is None:
                st.error("Copilot API unavailable. Please try again later or check service status.")
                assistant_msg = {
                    "role": "assistant",
                    "content": "I'm sorry, the Copilot service is currently unavailable. Please try again later.",
                    "citations": [],
                    "steps": [],
                }
            else:
                st.markdown(result.get("answer", ""))
                citations = result.get("citations", [])
                steps = result.get("intermediate_steps", [])
                if citations:
                    with st.expander("Sources", expanded=False):
                        for c in citations:
                            st.write(f"- {c}")
                if steps:
                    with st.expander("Tool steps", expanded=False):
                        for s in steps:
                            status = "✅" if s.get("success") else "❌"
                            st.write(
                                f"{status} {s.get('tool', '?')} ({s.get('execution_time_ms', 0):.0f}ms)"
                            )
                assistant_msg = {
                    "role": "assistant",
                    "content": result.get("answer", ""),
                    "citations": citations,
                    "steps": steps,
                }

        st.session_state.copilot_messages.append(assistant_msg)
