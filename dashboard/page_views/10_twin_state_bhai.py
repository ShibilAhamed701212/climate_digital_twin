"""Compatibility shim — Twin State (BHAI) merged into Digital Twin State."""  # noqa: N999

from __future__ import annotations

from importlib import import_module
from typing import Any

import streamlit as st


def render(api: Any, filters: dict) -> None:
    st.info(
        "Twin State (BHAI) was merged into **Digital Twin State**. "
        "Showing the unified page."
    )
    twin_state = import_module("dashboard.page_views.03_twin_state")
    twin_state.render(api, filters)
