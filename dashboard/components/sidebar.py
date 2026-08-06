"""Common sidebar controls and navigation."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.config.config import HORIZONS, PILOT_DISTRICTS, SAMPLE_LOCATIONS


def render_sidebar(api: Any | None = None) -> dict[str, Any]:
    """Render the common sidebar and return selected filters."""
    with st.sidebar:
        st.title("🌤 Climate Twin")
        st.caption("Karnataka — Pilot Region")

        st.divider()

        district = st.selectbox(
            "District",
            options=["All"] + PILOT_DISTRICTS,
            index=0,
            key="sidebar_district",
        )

        location_options = {
            f"{loc['district']} ({loc['id']})": loc["id"] for loc in SAMPLE_LOCATIONS
        }
        selected_location_label = st.selectbox(
            "Location",
            options=list(location_options.keys()),
            index=0,
            key="sidebar_location",
        )
        selected_location_id = location_options[selected_location_label]

        variable = st.selectbox(
            "Climate Variable",
            options=["Rainfall", "MaxTemp", "MinTemp"],
            index=0,
            key="sidebar_variable",
        )

        horizon = st.selectbox(
            "Forecast Horizon",
            options=list(HORIZONS.keys()),
            index=1,
            key="sidebar_horizon",
        )
        horizon_days = HORIZONS[horizon]

        if api is not None:
            status = api.get_pipeline_status(selected_location_id)
            if status["live"]:
                st.success("LIVE PIPELINE")
            else:
                st.error("PIPELINE NOT LIVE")
            failed = [name for name, ok in status["checks"].items() if not ok]
            with st.expander("Workflow status", expanded=False):
                for name, ok in status["checks"].items():
                    st.write(f"{'✅' if ok else '❌'} {name}")
                if failed:
                    st.caption("Failed: " + ", ".join(failed))

        st.divider()
        st.caption("About")
        st.markdown("AI-Powered Digital Twin of India's Climate. ISRO BAH 2026 — Challenge 5.")

    return {
        "district": district,
        "location_id": selected_location_id,
        "variable": variable,
        "horizon": horizon_days,
    }
