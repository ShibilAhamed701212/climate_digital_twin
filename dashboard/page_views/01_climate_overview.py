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
            current_data.append({**loc, "status": "unavailable"})

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Climate Map")
        m = climate_overlay_map(current_data, variable=variable)
        folium_static(m, width=None, height=500)

    with col2:
        st.subheader("Current Conditions")
        current = api.get_current_state(location_id)
        if current and current.get("status") != "unavailable":
            risk = api.get_risk(location_id)
            metric_card(
                "Rainfall", f"{current.get('rainfall', 0):.1f} mm", help_text="Last 24 hours"
            )
            metric_card("Current Temp", f"{current.get('current_temp', 0):.1f} °C")
            metric_card(
                "Risk Score",
                f"{risk['composite_risk']:.1f}" if risk else "Unavailable",
                help_text="Validated composite risk score",
            )

            ext = api.get_extended_conditions(location_id)
            if ext and ext.get("status") != "unavailable":
                with st.expander("More Live Conditions"):
                    _fmt = lambda v, u="": (  # noqa: E731
                        f"{v:.1f} {u}".strip() if isinstance(v, (int, float)) else "Unavailable"
                    )
                    _fmt_t = lambda v: v if isinstance(v, str) and v else "Unavailable"  # noqa: E731
                    st.markdown(
                        f"**Apparent Temperature:** {_fmt(ext.get('apparent_temperature'), '°C')}  \n"
                        f"**Daily Max / Min:** {_fmt(ext.get('daily_max_temp'), '°C')} / "
                        f"{_fmt(ext.get('daily_min_temp'), '°C')}  \n"
                        f"**Condition:** {ext.get('weather_code', 'Unavailable')}  \n"
                        f"**Wind Gusts:** {_fmt(ext.get('wind_gusts_10m'), 'km/h')}  \n"
                        f"**Precipitation Probability:** "
                        f"{_fmt(ext.get('precipitation_probability'), '%')}  \n"
                        f"**UV Index:** {_fmt(ext.get('uv_index'))}  \n"
                        f"**Sunrise / Sunset:** {_fmt_t(ext.get('sunrise'))} / "
                        f"{_fmt_t(ext.get('sunset'))}"
                    )
        else:
            st.info("No data available for selected location")

        st.divider()
        st.subheader("District Quick Stats")
        for loc in locations[:5]:
            s = api.get_current_state(loc["id"])
            if s:
                st.markdown(
                    f"**{loc['district']}** — Rain: {s.get('rainfall', 0):.1f}mm, "
                    f"Current: {s.get('current_temp', 0):.1f}°C"
                )

    st.divider()
    st.subheader("Historical Trend")
    hist = api.get_historical(location_id)
    if hist:
        fig = line_chart(
            hist, y_key=variable_to_field(variable), title=f"{variable} — Last 90 Days"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data available")
