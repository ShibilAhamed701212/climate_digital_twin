"""Page 3: Digital Twin State — unified current/history/forecast/versions/compare."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.time_series import multi_line_chart
from dashboard.components.cards import entity_detail_table, status_badge
from dashboard.maps.climate_map import climate_overlay_map
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("🔄 Digital Twin State")
    st.caption(
        "Live twin layers, historical records, forecasts, version history, and version comparison "
        "(merged former Twin State / BHAI browser)."
    )

    location_id = filters.get("location_id", "KA-BLR-001")
    variable = filters.get("variable", "Rainfall")

    current = api.get_current_state(location_id)
    historical = api.get_historical(location_id)
    forecast = api.get_forecast(location_id, horizon=3)
    versions = api.get_version_history(location_id)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Current State",
            "Historical",
            "Forecast State",
            "Version History",
            "Version Compare",
        ]
    )

    with tab1:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("Current State Map")
            locations = api.get_all_locations()
            current_data = []
            for loc in locations:
                s = api.get_current_state(loc["id"])
                if s and s.get("status") != "unavailable":
                    current_data.append(s)
            if current_data:
                m = climate_overlay_map(current_data, variable=variable)
                folium_static(m, width=None, height=450)
            else:
                st.info("No state data available")

        with col2:
            if current and current.get("status") != "unavailable":
                st.subheader("Entity Detail")
                status_badge("Active", "active")
                st.caption(
                    f"Source: {current.get('data_source', 'N/A')} · "
                    f"Quality: {current.get('quality_flag', 'N/A')}"
                )
                entity_detail_table(current)

                st.subheader("Key Variables")
                metrics = [
                    ("Temperature", f"{current.get('current_temp', current.get('max_temp', 'N/A'))}"),
                    ("Rainfall", f"{current.get('rainfall', 'N/A')} mm"),
                    ("Humidity", f"{current.get('humidity_pct', 'N/A')} %"),
                    ("Pressure", f"{current.get('pressure_hpa', 'N/A')} hPa"),
                    ("Wind", f"{current.get('wind_speed_10m', 'N/A')}"),
                ]
                mcols = st.columns(len(metrics))
                for i, (label, value) in enumerate(metrics):
                    mcols[i].metric(label, value)
            else:
                st.info("No current state data")

    with tab2:
        st.subheader("Historical State")
        if historical:
            fig = multi_line_chart(
                historical,
                title="Historical State Variables",
                y_keys=["rainfall", "max_temp", "min_temp"],
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Showing {len(historical)} historical records from the live twin")
        else:
            st.info("No historical state data")

    with tab3:
        st.subheader("Forecast State")
        if forecast:
            cols = st.columns(min(len(forecast), 3))
            for i, f in enumerate(forecast[:3]):
                with cols[i]:
                    st.markdown(f"**Day {i + 1}**")
                    st.metric("Rainfall", f"{f.get('rainfall', 0):.1f} mm")
                    st.metric("Max Temp", f"{f.get('max_temp', 0):.1f} °C")
                    st.metric("Min Temp", f"{f.get('min_temp', 0):.1f} °C")
                    st.caption(f"Confidence: {f.get('prediction_confidence', 0):.2f}")
        else:
            st.info("No forecast data available")

    with tab4:
        st.subheader("State Version History")
        if versions:
            rows = []
            for v in versions:
                state = v.get("state") if isinstance(v.get("state"), dict) else {}
                rows.append(
                    {
                        "Version": v.get("version_number", ""),
                        "Created": v.get("created_at", ""),
                        "Entity": v.get("entity_id", location_id),
                        "Rainfall": state.get("rainfall", state.get("precipitation_mm", "")),
                        "Temp": state.get("max_temp", state.get("temperature_2m", "")),
                        "Source": state.get("data_source", ""),
                    }
                )
            hist_df = pd.DataFrame(rows)
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

            if "Created" in hist_df.columns and hist_df["Created"].astype(str).str.len().gt(0).any():
                timeline = hist_df.copy()
                timeline["Created_dt"] = pd.to_datetime(timeline["Created"], errors="coerce")
                timeline = timeline.dropna(subset=["Created_dt"]).sort_values("Created_dt")
                if not timeline.empty:
                    st.subheader("Version Timeline")
                    st.line_chart(
                        timeline.rename(columns={"Created_dt": "Date", "Version": "Version"}),
                        x="Date",
                        y="Version",
                    )
        elif historical:
            # Fallback view from historical series when version store is thin
            version_data = []
            for i, h in enumerate(historical[-20:]):
                version_data.append(
                    {
                        "version": i + 1,
                        "timestamp": h.get("timestamp", ""),
                        "rainfall": h.get("rainfall", 0),
                        "state_type": h.get("state_type", "historical"),
                    }
                )
            st.dataframe(version_data, use_container_width=True)
            st.caption("Showing historical snapshots (version store empty/thin)")
        else:
            st.info("No version history available")

    with tab5:
        st.subheader("Version Comparison")
        max_v = 2
        if versions:
            nums = [int(v.get("version_number", 0) or 0) for v in versions]
            max_v = max(max(nums), 2)
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            version_a = st.number_input("Version A", min_value=1, max_value=max_v, value=1)
        with col_v2:
            version_b = st.number_input(
                "Version B",
                min_value=1,
                max_value=max_v,
                value=min(2, max_v),
            )

        if st.button("Compare Versions", type="primary", use_container_width=True):
            with st.spinner("Comparing versions..."):
                comparison = api.compare_versions(location_id, int(version_a), int(version_b))
                if comparison:
                    delta_df = pd.DataFrame(comparison)
                    st.dataframe(delta_df, use_container_width=True, hide_index=True)
                    if {"Variable", "Version A", "Version B"}.issubset(delta_df.columns):
                        compare_df = delta_df.melt(
                            id_vars=["Variable"],
                            value_vars=["Version A", "Version B"],
                            var_name="Version",
                            value_name="Value",
                        )
                        st.bar_chart(compare_df, x="Variable", y="Value", color="Version")
                else:
                    st.info("Version comparison unavailable for the selected pair.")

    st.divider()
    st.caption(f"Twin state data at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
