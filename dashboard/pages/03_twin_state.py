"""Page 3: Digital Twin State — state layers, version timeline, grid cell detail."""  # noqa: N999

from __future__ import annotations

import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.time_series import multi_line_chart
from dashboard.components.cards import entity_detail_table, status_badge
from dashboard.maps.climate_map import climate_overlay_map
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("🔄 Digital Twin State")
    st.caption("Real-time state layers, version history, and grid cell details")

    location_id = filters.get("location_id", "KA-BLR-001")
    variable = filters.get("variable", "Rainfall")

    current = api.get_current_state(location_id)
    historical = api.get_historical(location_id)
    forecast = api.get_forecast(location_id, horizon=3)

    tab1, tab2, tab3, tab4 = st.tabs(["Current State", "Historical", "Forecast State", "Version Timeline"])

    with tab1:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("Current State Map")
            locations = api.get_all_locations()
            current_data = []
            for loc in locations:
                s = api.get_current_state(loc["id"])
                if s:
                    current_data.append(s)
            if current_data:
                m = climate_overlay_map(current_data, variable=variable)
                folium_static(m, width=None, height=450)
            else:
                st.info("No state data available")

        with col2:
            if current:
                st.subheader("Entity Detail")
                status_badge("Active", "active")
                entity_detail_table(current)
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
            st.caption(f"Showing {len(historical)} historical records")
        else:
            st.info("No historical state data")

    with tab3:
        st.subheader("Forecast State")
        if forecast:
            col1, col2, col3 = st.columns(3)
            for i, f in enumerate(forecast):
                with [col1, col2, col3][i]:
                    st.markdown(f"**Day {i+1}**")
                    st.metric("Rainfall", f"{f.get('rainfall', 0):.1f} mm")
                    st.metric("Max Temp", f"{f.get('max_temp', 0):.1f} °C")
                    st.metric("Min Temp", f"{f.get('min_temp', 0):.1f} °C")
                    st.caption(f"Confidence: {f.get('prediction_confidence', 0):.2f}")
        else:
            st.info("No forecast data available")

    with tab4:
        st.subheader("State Version Timeline")
        if historical:
            version_data = []
            for i, h in enumerate(historical[-20:]):
                version_data.append({
                    "version": i + 1,
                    "timestamp": h.get("timestamp", ""),
                    "rainfall": h.get("rainfall", 0),
                    "state_type": h.get("state_type", "historical"),
                })
            st.dataframe(version_data, use_container_width=True)
            st.caption("Last 20 state versions shown")
        else:
            st.info("No version history available")
