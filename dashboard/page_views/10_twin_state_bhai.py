"""Page 10: Digital Twin State (BHAI variant) — entity state, version history, comparison."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

PILOT_DISTRICTS: list[dict[str, Any]] = [
    {"id": "mumbai", "name": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
    {"id": "delhi", "name": "Delhi", "state": "Delhi", "lat": 28.7041, "lon": 77.1025},
    {"id": "chennai", "name": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
    {"id": "kolkata", "name": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
    {"id": "hyderabad", "name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867},
    {"id": "bengaluru", "name": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    {"id": "ahmedabad", "name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714},
    {"id": "pune", "name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
]


def _district_options() -> list[str]:
    return sorted(f"{d['name']} ({d['state']})" for d in PILOT_DISTRICTS)


def _find_district(display_name: str) -> dict[str, Any] | None:
    for d in PILOT_DISTRICTS:
        if f"{d['name']} ({d['state']})" == display_name:
            return d
    return None


def _generate_sample_twin_data(entity_id: str) -> dict[str, Any]:
    np.random.seed(abs(hash(entity_id)) % 10000)
    return {
        "entity_id": entity_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "temperature_2m": round(float(np.random.uniform(22, 38)), 1),
        "precipitation_mm": round(float(np.random.exponential(2)), 1),
        "humidity_pct": round(float(np.random.uniform(40, 90)), 0),
        "pressure_hpa": round(float(np.random.normal(1013, 5)), 1),
        "wind_speed_10m": round(float(np.random.exponential(2)), 1),
        "data_source": "synthetic",
        "quality_flag": "validated",
    }


def _generate_sample_twin_history(entity_id: str) -> list[dict[str, Any]]:
    np.random.seed(abs(hash(entity_id)) % 10000)
    history = []
    for i in range(5, 0, -1):
        from datetime import timedelta

        history.append(
            {
                "version_number": i,
                "created_at": (datetime.now(UTC) - timedelta(days=i * 7)).isoformat(),
                "created_by": np.random.choice(["api", "manual", "sync"]),
                "description": f"State version {i}",
            }
        )
    return history


def render(api: Any, filters: dict) -> None:  # noqa: ARG001
    st.header("Digital Twin State Browser")
    st.markdown("Browse digital twin entity states, version history, and compare versions.")

    with st.sidebar:
        st.subheader("Entity Selection")
        selected_district = st.selectbox(
            "Select Entity", options=_district_options(), index=0, key="twin_location"
        )
        district = _find_district(selected_district)

        view_mode = st.radio(
            "View Mode",
            ["Current State", "Version History", "Version Comparison"],
            key="twin_view_mode",
        )

        refresh_btn = st.button("Refresh", type="primary", use_container_width=True)

    if district is None:
        st.warning("Please select a valid location.")
        st.stop()

    entity_id = district["id"]

    if view_mode == "Current State":
        if refresh_btn or "twin_state" not in st.session_state:
            with st.spinner(f"Loading state for {district['name']}..."):
                state = _generate_sample_twin_data(entity_id)
                st.session_state["twin_state"] = state

        state = st.session_state.get("twin_state", {})

        if not state:
            st.warning("No state data available.")
            st.stop()

        st.subheader(f"Entity: {district['name']}")

        col1, col2, col3 = st.columns(3)
        col1.info(f"**Entity ID:** {state.get('entity_id', entity_id)}")
        col2.info(f"**Data Source:** {state.get('data_source', 'N/A')}")
        col3.info(f"**Quality:** {state.get('quality_flag', 'N/A')}")

        st.caption(f"Last updated: {state.get('timestamp', 'N/A')}")

        st.subheader("Current State Variables")

        state_vars = [
            ("Temperature", f"{state.get('temperature_2m', 'N/A')} C"),
            ("Precipitation", f"{state.get('precipitation_mm', 'N/A')} mm"),
            ("Humidity", f"{state.get('humidity_pct', 'N/A')} %"),
            ("Pressure", f"{state.get('pressure_hpa', 'N/A')} hPa"),
            ("Wind Speed", f"{state.get('wind_speed_10m', 'N/A')} m/s"),
        ]

        var_cols = st.columns(5)
        for i, (label, value) in enumerate(state_vars):
            with var_cols[i]:
                st.metric(label, value)

        st.subheader("State Values Overview")

        gauge_data = pd.DataFrame(
            {
                "Variable": ["Temperature", "Precipitation", "Humidity", "Pressure", "Wind Speed"],
                "Value": [
                    state.get("temperature_2m", 0),
                    state.get("precipitation_mm", 0),
                    state.get("humidity_pct", 0),
                    state.get("pressure_hpa", 1013),
                    state.get("wind_speed_10m", 0),
                ],
            }
        )
        st.bar_chart(gauge_data, x="Variable", y="Value")

    elif view_mode == "Version History":
        if refresh_btn or "twin_history" not in st.session_state:
            with st.spinner(f"Loading history for {district['name']}..."):
                history = _generate_sample_twin_history(entity_id)
                st.session_state["twin_history"] = history

        history = st.session_state.get("twin_history", [])

        st.subheader(f"Version History — {district['name']}")

        if not history:
            st.info("No version history available.")
        else:
            hist_df = pd.DataFrame(history)
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

            st.subheader("State Timeline")
            if "created_at" in hist_df.columns:
                hist_df["created_at_dt"] = pd.to_datetime(hist_df["created_at"])
                hist_df = hist_df.sort_values("created_at_dt")
                timeline_df = pd.DataFrame(
                    {
                        "Date": hist_df["created_at_dt"],
                        "Version": hist_df["version_number"],
                    }
                )
                st.line_chart(timeline_df, x="Date", y="Version")

    elif view_mode == "Version Comparison":
        st.subheader("Version Comparison")

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            version_a = st.number_input("Version A", min_value=1, max_value=100, value=1)
        with col_v2:
            version_b = st.number_input("Version B", min_value=1, max_value=100, value=2)

        if st.button("Compare Versions", type="primary", use_container_width=True):
            with st.spinner("Comparing versions..."):
                np.random.seed(version_a * 100 + version_b)

                delta_data = {
                    "Variable": [
                        "Temperature (C)",
                        "Precipitation (mm)",
                        "Humidity (%)",
                        "Pressure (hPa)",
                        "Wind Speed (m/s)",
                    ],
                    "Version A": [
                        float(np.random.uniform(22, 35)),
                        float(np.random.exponential(3)),
                        float(np.random.uniform(40, 80)),
                        float(np.random.normal(1013, 5)),
                        float(np.random.exponential(2)),
                    ],
                    "Version B": [
                        float(np.random.uniform(22, 35)),
                        float(np.random.exponential(3)),
                        float(np.random.uniform(40, 80)),
                        float(np.random.normal(1013, 5)),
                        float(np.random.exponential(2)),
                    ],
                }

                delta_df = pd.DataFrame(delta_data)
                delta_df["Delta"] = delta_df["Version B"] - delta_df["Version A"]
                delta_df["Change %"] = ((delta_df["Delta"] / delta_df["Version A"]) * 100).round(2)

                st.dataframe(delta_df, use_container_width=True, hide_index=True)

                st.subheader("Visual Comparison")
                compare_df = delta_df.melt(
                    id_vars=["Variable"],
                    value_vars=["Version A", "Version B"],
                    var_name="Version",
                    value_name="Value",
                )
                st.bar_chart(compare_df, x="Variable", y="Value", color="Version")

    st.divider()
    st.caption(f"Twin state data at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
