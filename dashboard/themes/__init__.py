"""Theme configuration for Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

STREAMLIT_THEME = {
    "theme": {
        "primaryColor": "#1a1a2e",
        "backgroundColor": "#f8f9fa",
        "secondaryBackgroundColor": "#ffffff",
        "textColor": "#1a1a2e",
        "font": "sans serif",
    }
}


def apply_theme() -> None:
    for key, value in STREAMLIT_THEME["theme"].items():
        st.config.set_option(key, value)
