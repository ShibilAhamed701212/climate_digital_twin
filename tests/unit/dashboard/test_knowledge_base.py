"""Tests for dashboard/pages/08_knowledge_base.py — render() function."""

from __future__ import annotations

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _clear_kb_session():
    if "kb_results" in st.session_state:
        del st.session_state.kb_results
    if "selected_collection" in st.session_state:
        del st.session_state.selected_collection


def test_knowledge_base_render_does_not_crash():
    m = __import__("dashboard.page_views.08_knowledge_base", fromlist=["render"])

    m.render(None, {})
    assert True


def test_knowledge_base_with_session_results():
    st.session_state["kb_results"] = [
        {
            "rank": 1,
            "score": 0.95,
            "document_id": "doc_1",
            "chunk_id": "chunk_1",
            "text": "Sample document content related to 'climate'.",
        }
    ]
    m = __import__("dashboard.page_views.08_knowledge_base", fromlist=["render"])

    m.render(None, {})
    assert True


def test_knowledge_base_with_selected_collection():
    st.session_state["selected_collection"] = "imd_reports"
    m = __import__("dashboard.page_views.08_knowledge_base", fromlist=["render"])

    m.render(None, {})
    assert True
