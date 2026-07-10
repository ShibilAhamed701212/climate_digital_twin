"""Sidebar page navigation — replaces Streamlit's auto-generated page nav."""

from __future__ import annotations

import streamlit as st

from dashboard.config.config import PAGES


def render_sidebar_nav() -> None:
    """Render page navigation links in the sidebar."""
    st.sidebar.divider()
    st.sidebar.subheader("Navigation")

    current = st.session_state.get("page", PAGES[0]["file"])

    opts = {p["title"]: p["file"] for p in PAGES}
    current_idx = next(i for i, p in enumerate(PAGES) if p["file"] == current)

    selected_title = st.sidebar.radio(
        "Go to",
        options=list(opts.keys()),
        index=current_idx,
        key="sidebar_nav_radio",
        label_visibility="collapsed",
    )
    selected_file = opts[selected_title]

    if selected_file != current:
        st.session_state.page = selected_file
        st.rerun()
