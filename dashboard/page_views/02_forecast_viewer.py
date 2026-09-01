"""Page 2: Forecast Viewer — prediction maps and confidence indicators."""  # noqa: N999

from __future__ import annotations

import streamlit as st
from streamlit_folium import folium_static

from dashboard.charts.time_series import confidence_band_chart
from dashboard.components.cards import entity_detail_table, metric_card
from dashboard.config.config import variable_to_field
from dashboard.maps.climate_map import forecast_map
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("📈 Forecast Viewer")
    st.caption("AI-powered climate predictions with confidence indicators")

    location_id = filters.get("location_id", "KA-BLR-001")
    variable = filters.get("variable", "Rainfall")
    horizon = filters.get("horizon", 3)

    current = api.get_current_state(location_id)
    forecasts = api.get_forecast(location_id, horizon=horizon)

    # Show fallback notice if fewer predictions than requested
    if forecasts and len(forecasts) < horizon:
        st.info(
            f"Showing {len(forecasts)} of {horizon} requested days. "
            f"Full multi-day forecast unavailable via gateway (model loading issue); "
            f"using direct LSTM engine prediction."
        )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader(f"{horizon}-Day Forecast Map")
        if current:
            m = forecast_map(current, forecasts, variable=variable)
            folium_static(m, width=None, height=450)
        else:
            st.info("No current data available")

    with col2:
        if forecasts:
            st.subheader("Forecast Summary")
            latest = forecasts[-1]
            metric_card(
                f"Predicted {variable}",
                f"{latest.get(variable_to_field(variable), 0):.1f}",
                help_text=f"Day {horizon} forecast",
            )
            conf = latest.get("prediction_confidence", 0)
            conf_label = f"{conf:.2f}" if conf > 0 else "N/A (model fallback)"
            metric_card(
                "Confidence",
                conf_label,
                help_text="Model confidence (0-1)",
            )
            model_src = latest.get("model_id", "") or latest.get("data_source", "")
            if model_src:
                st.caption(f"Model: {model_src}")
            st.divider()
            st.subheader("Day-by-Day")
            for i, f in enumerate(forecasts):
                val = f.get(variable_to_field(variable), 0)
                day_conf = f.get("prediction_confidence", 0)
                conf_str = f"{day_conf:.2f}" if day_conf > 0 else "N/A"
                st.markdown(f"**Day {i + 1}:** {val:.1f} (confidence: {conf_str})")

    st.divider()
    st.subheader("Forecast Confidence Trend")
    if forecasts:
        fig = confidence_band_chart(
            forecasts,
            y_key=variable_to_field(variable),
            title=f"{variable} Forecast with Confidence Bands",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Conditions")
        if current:
            entity_detail_table(current)

    with col2:
        st.subheader("Download Forecast")
        st.download_button(
            label="📥 Download Forecast Data (CSV)",
            data=_forecast_csv(forecasts),
            file_name=f"forecast_{location_id}_{horizon}day.csv",
            mime="text/csv",
        )


def _forecast_csv(forecasts: list[dict]) -> str:
    if not forecasts:
        return ""
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=forecasts[0].keys())
    writer.writeheader()
    writer.writerows(forecasts)
    return output.getvalue()
