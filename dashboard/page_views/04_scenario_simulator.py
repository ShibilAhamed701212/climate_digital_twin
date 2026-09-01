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

    scenario_id: str | None = None
    with col1:
        st.subheader("Scenario Configuration")
        scenario_options = {
            s.get("name", f"Scenario {i}"): s.get("id", str(i)) for i, s in enumerate(scenarios)
        }
        if scenario_options:
            selected_scenario = st.selectbox(
                "Preset Scenario",
                options=list(scenario_options.keys()),
                index=0,
                key="scenario_preset",
            )
            scenario_id = scenario_options[selected_scenario]

            selected_scenario_data = next(
                (s for s in scenarios if s.get("id") == scenario_id), scenarios[0]
            )
            info_card(
                selected_scenario_data["name"],
                selected_scenario_data.get("description", ""),
                icon="📋",
            )
        else:
            st.info("No preset scenarios available — use custom parameters below")

        st.divider()
        st.markdown("**Custom Parameters**")
        params = scenario_parameters()

        simulate_btn = st.button("🚀 Run Simulation", type="primary", use_container_width=True)

    current = api.get_current_state(location_id)
    if current is not None and current.get("status") == "unavailable":
        current = None

    with col2:
        if simulate_btn and current:
            sim_params = {
                "scenario_id": scenario_id or "custom",
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
                    before_val = float(current.get(var_key) or 0)
                    after_val = float(scenario_state.get(var_key) or 0)

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
            st.info(
                "Select a location and configure scenario parameters, then click 'Run Simulation'"
            )

    st.divider()
    st.subheader("Advanced Simulation Tools")

    adv_tab1, adv_tab2, adv_tab3 = st.tabs(
        ["Monte Carlo", "Scenario Comparison", "Ensemble Forecast"]
    )

    with adv_tab1:
        st.markdown("**Monte Carlo Simulation** — probabilistic analysis with confidence intervals")
        mc_col1, mc_col2 = st.columns(2)
        with mc_col1:
            mc_type = st.selectbox(
                "Scenario Type",
                ["temperature", "rainfall", "extreme_event"],
                key="mc_type",
            )
        with mc_col2:
            mc_runs = st.number_input("Simulations", 100, 10000, 500, step=100, key="mc_runs")

        _mc_delta = st.slider("Temperature Delta (°C)", -5.0, 10.0, 2.0, key="mc_delta")

        if st.button("Run Monte Carlo", key="mc_btn"):
            mc_result = api.run_monte_carlo(
                scenario_type=mc_type,
                base_params={
                    "location_id": location_id,
                    "latitude": filters.get("latitude", 12.97),
                    "longitude": filters.get("longitude", 77.59),
                    "temperature_2m": (current.get("max_temp") if current else None) or 25.0,
                },
                num_simulations=mc_runs,
            )
            if mc_result:
                st.success(f"Completed {mc_result['n_samples']} simulations")
                summary = mc_result.get("summary", {})
                cis = mc_result.get("confidence_intervals", {})
                if summary:
                    st.markdown("**Summary Statistics**")
                    st.json(summary)
                if cis:
                    st.markdown("**Confidence Intervals (95%)**")
                    rows = []
                    for var, ci in cis.items():
                        rows.append(
                            {
                                "Variable": var,
                                "Mean": f"{ci.get('mean', 0):.3f}",
                                "Lower CI": f"{ci.get('lower', 0):.3f}",
                                "Upper CI": f"{ci.get('upper', 0):.3f}",
                                "Std": f"{ci.get('std', 0):.3f}",
                            }
                        )
                    st.table(rows)
            else:
                st.warning("Monte Carlo simulation unavailable")

    with adv_tab2:
        st.markdown("**Scenario Comparison** — compare multiple scenarios side by side")
        compare_configs = []
        num_compare = st.number_input("Number of scenarios", 2, 5, 2, key="num_compare")
        for i in range(num_compare):
            with st.expander(f"Scenario {i + 1}", expanded=i == 0):
                name = st.text_input("Name", f"Scenario {i + 1}", key=f"cmp_name_{i}")
                s_type = st.selectbox(
                    "Type",
                    ["temperature", "rainfall", "extreme_event"],
                    key=f"cmp_type_{i}",
                )
                delta = st.number_input("Temperature Delta", -5.0, 10.0, 0.0, key=f"cmp_delta_{i}")
                compare_configs.append(
                    {
                        "name": name,
                        "scenario_type": s_type,
                        "parameters": {"temperature_delta": delta},
                        "location_id": location_id,
                    }
                )

        if st.button("Compare Scenarios", key="cmp_btn") and len(compare_configs) >= 2:
            cmp_result = api.compare_scenarios(compare_configs)
            if cmp_result and cmp_result.get("comparisons"):
                st.success(f"{cmp_result['total_comparisons']} comparison(s) generated")
                for comp in cmp_result["comparisons"]:
                    st.markdown(f"**{comp['scenario_a']} vs {comp['scenario_b']}**")
                    st.caption(comp.get("summary", ""))
                    deltas = comp.get("variable_deltas", {})
                    if deltas:
                        delta_rows = []
                        for var, d in deltas.items():
                            delta_rows.append(
                                {
                                    "Variable": var,
                                    "Mean Delta": f"{d.get('mean', 0):+.3f}",
                                    "Max Delta": f"{d.get('max', 0):+.3f}",
                                    "Min Delta": f"{d.get('min', 0):+.3f}",
                                }
                            )
                        st.table(delta_rows)
                    sig = comp.get("significant_variables", [])
                    if sig:
                        st.info(f"Significant: {', '.join(sig)}")
            else:
                st.warning("Comparison unavailable")

    with adv_tab3:
        st.markdown("**Ensemble Forecast** — multi-member ensemble analysis")
        ens_members = st.number_input("Members", 2, 20, 5, key="ens_members")
        ens_delta = st.slider("Base Temperature Delta (°C)", -5.0, 10.0, 1.0, key="ens_delta")

        if st.button("Run Ensemble", key="ens_btn"):
            members = [
                {
                    "config": {
                        "name": f"Member {i + 1}",
                        "scenario_type": "temperature",
                        "parameters": {"temperature_delta": ens_delta * (1 + 0.2 * i)},
                        "location_id": location_id,
                    },
                    "weight": 1.0,
                }
                for i in range(ens_members)
            ]
            ens_result = api.run_ensemble(members, location_id=location_id)
            if ens_result:
                st.success(f"Ensemble with {ens_result['n_members']} members completed")
                summary = ens_result.get("summary", {})
                ens_mean = ens_result.get("ensemble_mean", {})
                _ens_spread = ens_result.get("ensemble_spread", {})

                if summary:
                    st.markdown("**Ensemble Summary**")
                    rows = []
                    for var, s in summary.items():
                        rows.append(
                            {
                                "Variable": var,
                                "Mean": f"{s.get('ensemble_mean', 0):.3f}",
                                "Std": f"{s.get('ensemble_std', 0):.3f}",
                                "P5": f"{s.get('ensemble_p5', 0):.3f}",
                                "P95": f"{s.get('ensemble_p95', 0):.3f}",
                            }
                        )
                    st.table(rows)

                if ens_mean:
                    st.markdown("**Ensemble Mean (first 12 time steps)**")
                    for var, vals in ens_mean.items():
                        st.caption(f"{var}: {', '.join(f'{v:.2f}' for v in vals[:12])}...")
            else:
                st.warning("Ensemble simulation unavailable")

    st.divider()
    st.subheader("Available Scenarios")
    for s in scenarios:
        with st.expander(s.get("name", "Unnamed")):
            st.markdown(f"**ID:** `{s.get('id', 'N/A')}`")
            st.markdown(s.get("description", "No description"))
