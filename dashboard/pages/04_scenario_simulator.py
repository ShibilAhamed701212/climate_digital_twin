"""Page 4: Scenario Simulator — what-if analysis with before/after comparison."""  # noqa: N999

from __future__ import annotations

import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.comparison import before_after_chart
from dashboard.components.cards import info_card, metric_card
from dashboard.components.filters import scenario_parameters
from dashboard.config.config import variable_to_field
from dashboard.maps.comparison_map import before_after_comparison, delta_map
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("🔮 Scenario Simulator")
    st.caption("What-if analysis — simulate climate scenarios and visualize impacts")

    location_id = filters.get("location_id", "KA-BLR-001")
    variable = filters.get("variable", "Rainfall")

    scenarios = api.get_scenarios()

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Scenario Configuration")
        scenario_options = {s["name"]: s["id"] for s in scenarios}
        selected_scenario = st.selectbox(
            "Preset Scenario",
            options=list(scenario_options.keys()),
            index=0,
            key="scenario_preset",
        )
        scenario_id = scenario_options[selected_scenario]

        selected_scenario_data = next((s for s in scenarios if s["id"] == scenario_id), scenarios[0])
        info_card(
            selected_scenario_data["name"],
            selected_scenario_data.get("description", ""),
            icon="📋",
        )

        st.divider()
        st.markdown("**Custom Parameters**")
        params = scenario_parameters()

        simulate_btn = st.button("🚀 Run Simulation", type="primary", use_container_width=True)

    current = api.get_current_state(location_id)

    with col2:
        if simulate_btn and current:
            sim_params = {
                "scenario_id": scenario_id,
                "location_id": location_id,
                **params,
            }
            result = api.simulate_scenario(sim_params)

            if result and "data" in result:
                scenario_state = result["data"]

                st.subheader("Simulation Results")

                tab1, tab2, tab3 = st.tabs(["Comparison", "Map View", "Delta"])

                with tab1:
                    col_a, col_b, col_c = st.columns(3)
                    var_key = variable_to_field(variable)
                    before_val = current.get(var_key, 0)
                    after_val = scenario_state.get(var_key, 0)

                    with col_a:
                        metric_card("Before", f"{before_val:.1f}")
                    with col_b:
                        metric_card("After", f"{after_val:.1f}")
                    with col_c:
                        delta = after_val - before_val
                        metric_card("Delta", f"{delta:+.1f}", delta=f"{delta:+.1f}")

                    fig = before_after_chart(current, scenario_state, variable=variable)
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    m = before_after_comparison(current, scenario_state, variable=variable)
                    folium_static(m, width=None, height=400)

                with tab3:
                    m = delta_map(current, scenario_state, variable=variable)
                    folium_static(m, width=None, height=400)
            else:
                st.warning("Simulation did not return results")
        elif not current:
            st.info("Select a location and configure scenario parameters, then click 'Run Simulation'")

    st.divider()
    st.subheader("Available Scenarios")
    for s in scenarios:
        with st.expander(f"{s['name']}"):
            st.markdown(f"**ID:** `{s['id']}`")
            st.markdown(s.get("description", "No description"))
