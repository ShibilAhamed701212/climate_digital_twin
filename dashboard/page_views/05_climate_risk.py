"""Page 5: Climate Risk — risk scores, SHAP explanations, district ranking."""  # noqa: N999

from __future__ import annotations

import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.comparison import comparison_bar
from dashboard.charts.risk_trends import (
    risk_category_chart,
    risk_gauge,
    risk_trend_chart,
    shap_waterfall,
)
from dashboard.components.cards import metric_card
from dashboard.maps.climate_map import risk_heatmap
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("⚠️ Climate Risk")
    st.caption("Risk scores, deterministic feature attribution, and district rankings")
    st.info(
        "Scores come from the live twin/Open-Meteo pipeline through `/risk/assess` "
        "(heat + heavy rain + dryness → weighted composite). "
        "They are not synthetic placeholders."
    )

    location_id = filters.get("location_id", "KA-BLR-001")

    locations = api.get_all_locations()
    risk_data_list = []
    for loc in locations:
        risk = api.get_risk(loc["id"])
        if risk:
            risk_data_list.append(risk)

    risk_data = api.get_risk(location_id)
    current = api.get_current_state(location_id)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Risk Map", "District Ranking", "Risk Analysis", "Feature Attribution"]
    )

    with tab1:
        st.subheader("Composite Risk Heatmap")
        if risk_data_list:
            m = risk_heatmap(risk_data_list)
            folium_static(m, width=None, height=500)
        else:
            st.info("No risk data available")

    with tab2:
        st.subheader("District Risk Ranking")
        if risk_data_list:
            sorted_risks = sorted(
                risk_data_list, key=lambda x: x.get("composite_risk", 0), reverse=True
            )
            fig = comparison_bar(
                sorted_risks,
                x_key="district",
                y_key="composite_risk",
                title="Composite Risk by District",
                color_col="composite_risk",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Ranking Table")
            rank_data = []
            for i, r in enumerate(sorted_risks, 1):
                rank_data.append(
                    {
                        "Rank": i,
                        "District": r.get("district", ""),
                        "Composite": round(float(r.get("composite_risk", 0) or 0), 2),
                        "Heat": round(float(r.get("heat_risk", 0) or 0), 2),
                        "Heavy Rain": round(float(r.get("flood_risk", 0) or 0), 2),
                        "Dryness": round(float(r.get("drought_risk", 0) or 0), 2),
                        "Source": (r.get("inputs") or {}).get(
                            "data_source", r.get("data_source", "")
                        ),
                    }
                )
            st.dataframe(rank_data, use_container_width=True)
        else:
            st.info("No risk data available")

    with tab3:
        if risk_data:
            col1, col2 = st.columns([1, 2])

            with col1:
                st.subheader("Composite Score")
                fig = risk_gauge(risk_data.get("composite_risk", 0))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Risk Breakdown")
                fig = risk_category_chart(risk_data)
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Risk Trend")
            fig = risk_trend_chart(risk_data, title="Risk Score Trend (Monthly)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk analysis data available")

    with tab4:
        st.subheader("Deterministic Feature Attribution")
        if risk_data and "shap_summary" in risk_data:
            fig = shap_waterfall(risk_data["shap_summary"])
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "These are real rule-based attribution values from the validated hazard assessment, "
                "not model SHAP values."
            )

            st.divider()
            st.info(
                "SHAP (SHapley Additive exPlanations) explains how each climate variable "
                "contributes to the overall risk score. Positive values increase risk, "
                "negative values decrease it."
            )
        else:
            st.info("No SHAP explanation data available")

        if current:
            st.subheader("Current Conditions")
            col1, col2, col3 = st.columns(3)
            with col1:
                metric_card("Rainfall", f"{current.get('rainfall', 0):.1f} mm")
            with col2:
                metric_card("Current Temp", f"{current.get('current_temp', 0):.1f} °C")
            with col3:
                metric_card("Daily Extremes", "Unavailable")
