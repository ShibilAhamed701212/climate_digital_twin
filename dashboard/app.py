"""Main entry point for the Climate Digital Twin Streamlit dashboard."""

from __future__ import annotations

import logging

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.config.config import PAGE_CONFIG, PAGES
from dashboard.services.api_client import create_api_client

logger = logging.getLogger(__name__)


def _load_css() -> None:
    try:
        with open("dashboard/assets/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


def _init_session() -> None:
    if "api" not in st.session_state:
        st.session_state.api = create_api_client()
    if "page" not in st.session_state:
        st.session_state.page = PAGES[0]["file"]


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)
    _load_css()
    _init_session()

    filters = render_sidebar()
    api = st.session_state.api

    page_file = st.session_state.get("page", PAGES[0]["file"])

    col1, col2 = st.columns([1, 5])
    with col1:
        page_options = {p["title"]: p["file"] for p in PAGES}
        selected_title = st.selectbox(
            "Navigate",
            options=list(page_options.keys()),
            index=0,
            label_visibility="collapsed",
            key="nav_select",
        )
        st.session_state.page = page_options[selected_title]
        page_file = st.session_state.page

    st.divider()

    try:
        page_module = __import__(
            f"dashboard.pages.{page_file}",
            fromlist=["render"],
        )
        page_module.render(api, filters)
    except ImportError as e:
        st.error(f"Page not found: {page_file}. Error: {e}")
        logger.exception("Failed to load page %s", page_file)


if __name__ == "__main__":
    main()
