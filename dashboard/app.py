"""Main entry point for the Climate Digital Twin Streamlit dashboard."""

from __future__ import annotations

import logging
import traceback

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.components.sidebar_nav import render_sidebar_nav
from dashboard.config.config import PAGE_CONFIG, PAGES
from dashboard.services.api_client import create_api_client

logger = logging.getLogger(__name__)


def _load_css() -> None:
    try:
        with open("dashboard/assets/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        logger.warning("CSS file not found at dashboard/assets/style.css — using defaults")


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

    # Sidebar page navigation replaces Streamlit's auto-generated nav
    render_sidebar_nav()

    page_file = st.session_state.get("page", PAGES[0]["file"])

    try:
        page_module = __import__(
            f"dashboard.page_views.{page_file}",
            fromlist=["render"],
        )
    except Exception as e:
        logger.exception("Import failed for page %s", page_file)
        st.error(f"Failed to import page '{page_file}': {type(e).__name__}: {e}")
        st.code(traceback.format_exc(), language="text")
        return

    try:
        page_module.render(api, filters)
    except Exception as e:
        logger.exception("Render failed for page %s", page_file)
        st.error(f"Page '{page_file}' crashed: {type(e).__name__}: {e}")
        st.code(traceback.format_exc(), language="text")


if __name__ == "__main__":
    main()
