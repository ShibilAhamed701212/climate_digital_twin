"""Page 1: Climate Overview — interactive map and current conditions."""  # noqa: N999

from __future__ import annotations

import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.time_series import line_chart
from dashboard.components.cards import metric_card
from dashboard.config.config import variable_to_field
from dashboard.maps.climate_map import climate_overlay_map
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("🌍 Climate Overview")
    st.caption("Current climate conditions across Karnataka with district-level data")

    locations = api.get_all_locations()
    variable = filters.get("variable", "Rainfall")
    location_id = filters.get("location_id", locations[0]["id"])

    current_data = []
    for loc in locations:
        state = api.get_current_state(loc["id"])
        if state:
            current_data.append(state)
        else:
            current_data.append({
                "location_id": loc["id"],
                "latitude": loc["lat"],
                "longitude": loc["lon"],
                "district": loc["district"],
                "rainfall": 0,
                "max_temp": 25,
                "min_temp": 18,
                "risk_score": 0,
            })

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Climate Map")
        m = climate_overlay_map(current_data, variable=variable)
        folium_static(m, width=None, height=500)

    with col2:
        st.subheader("Current Conditions")
        current = api.get_current_state(location_id)
        if current:
            metric_card("Rainfall", f"{current.get('rainfall', 0):.1f} mm", help_text="Last 24 hours")
            metric_card("Max Temp", f"{current.get('max_temp', 0):.1f} °C", help_text="Today's maximum")
            metric_card("Min Temp", f"{current.get('min_temp', 0):.1f} °C", help_text="Today's minimum")
            metric_card("Risk Score", f"{current.get('risk_score', 0):.1f}", help_text="Composite climate risk")
        else:
            st.info("No data available for selected location")

        st.divider()
        st.subheader("District Quick Stats")
        for loc in locations[:5]:
            s = api.get_current_state(loc["id"])
            if s:
                st.markdown(f"**{loc['district']}** — Rain: {s.get('rainfall', 0):.1f}mm, "
                          f"Max: {s.get('max_temp', 0):.1f}°C, Min: {s.get('min_temp', 0):.1f}°C")

    st.divider()
    st.subheader("Historical Trend")
    hist = api.get_historical(location_id)
    if hist:
        fig = line_chart(hist, y_key=variable_to_field(variable), title=f"{variable} — Last 90 Days")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data available")
