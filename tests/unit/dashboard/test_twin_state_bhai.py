"""Tests for dashboard/pages/10_twin_state_bhai.py — render() function."""

from __future__ import annotations

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _clear_twin_session():
    for k in ["twin_location", "twin_view_mode", "twin_state", "twin_history"]:
        if k in st.session_state:
            del st.session_state[k]


def test_twin_state_bhai_render_current_state():
    st.session_state["twin_location"] = "Bengaluru (Karnataka)"
    st.session_state["twin_view_mode"] = "Current State"
    m = __import__("dashboard.page_views.10_twin_state_bhai", fromlist=["render"])

    m.render(None, {})
    assert True


def test_twin_state_bhai_render_version_history():
    st.session_state["twin_location"] = "Bengaluru (Karnataka)"
    st.session_state["twin_view_mode"] = "Version History"
    m = __import__("dashboard.page_views.10_twin_state_bhai", fromlist=["render"])

    m.render(None, {})
    assert True


def test_twin_state_bhai_render_version_comparison():
    st.session_state["twin_location"] = "Bengaluru (Karnataka)"
    st.session_state["twin_view_mode"] = "Version Comparison"
    m = __import__("dashboard.page_views.10_twin_state_bhai", fromlist=["render"])

    m.render(None, {})
    assert True


def test_twin_state_bhai_current_state_cached():
    st.session_state["twin_location"] = "Bengaluru (Karnataka)"
    st.session_state["twin_view_mode"] = "Current State"
    st.session_state["twin_state"] = {
        "entity_id": "bengaluru",
        "timestamp": "2024-01-01T00:00:00",
        "temperature_2m": 28.5,
        "precipitation_mm": 10.2,
        "humidity_pct": 65,
        "pressure_hpa": 1012,
        "wind_speed_10m": 3.5,
        "data_source": "synthetic",
        "quality_flag": "validated",
    }
    m = __import__("dashboard.page_views.10_twin_state_bhai", fromlist=["render"])

    m.render(None, {})
    assert True


def test_twin_state_bhai_version_history_cached():
    st.session_state["twin_location"] = "Bengaluru (Karnataka)"
    st.session_state["twin_view_mode"] = "Version History"
    st.session_state["twin_history"] = [
        {
            "version_number": 1,
            "created_at": "2024-01-01T00:00:00",
            "created_by": "api",
            "description": "v1",
        },
        {
            "version_number": 2,
            "created_at": "2024-01-08T00:00:00",
            "created_by": "manual",
            "description": "v2",
        },
    ]
    m = __import__("dashboard.page_views.10_twin_state_bhai", fromlist=["render"])

    m.render(None, {})
    assert True
