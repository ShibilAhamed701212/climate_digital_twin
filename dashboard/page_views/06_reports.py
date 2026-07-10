"""Page 6: Reports & Insights — auto-generated reports, district summaries, exports."""  # noqa: N999

from __future__ import annotations

from datetime import datetime

import streamlit as st

from dashboard.charts.comparison import grouped_comparison
from dashboard.charts.distribution import histogram, scatter_plot
from dashboard.charts.time_series import line_chart
from dashboard.components.cards import metric_card
from dashboard.config.config import variable_to_field
from dashboard.services.api_client import DashboardAPI


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("📊 Reports & Insights")
    st.caption("Auto-generated climate reports, district summaries, and exportable data")

    location_id = filters.get("location_id", "KA-BLR-001")
    district = filters.get("district", "All")

    districts = []
    if district == "All":
        districts = [loc["district"] for loc in api.get_all_locations()]
    else:
        districts = [district]

    tab1, tab2, tab3, tab4 = st.tabs(
        ["District Summary", "Data Explorer", "Export", "Report Generator"]
    )

    with tab1:
        st.subheader("District-Level Climate Summary")
        summary_data = []
        for d in districts:
            summary = api.get_district_summary(d)
            summary_data.append(summary)
            with st.expander(f"{d}", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    metric_card(
                        "Total Rainfall (YTD)", f"{summary.get('total_rainfall_ytd', 0):.1f} mm"
                    )
                with col2:
                    metric_card("Avg Max Temp", f"{summary.get('avg_max_temp', 0):.1f} °C")
                with col3:
                    metric_card("Rainy Days", f"{summary.get('rainy_days', 0)}")
                with col4:
                    metric_card("Risk Level", summary.get("risk_level", "N/A"))

        if summary_data:
            st.subheader("District Comparison")
            fig = grouped_comparison(
                summary_data,
                x_key="district",
                y_keys=["total_rainfall_ytd", "avg_max_temp", "avg_min_temp"],
                title="District Climate Comparison",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Climate Data Explorer")
        historical = api.get_historical(location_id)

        explore_var = st.selectbox(
            "Variable",
            options=["Rainfall", "MaxTemp", "MinTemp"],
            index=0,
            key="explore_var",
        )

        if historical:
            col1, col2 = st.columns(2)

            with col1:
                fig = line_chart(
                    historical,
                    y_key=variable_to_field(explore_var),
                    title=f"{explore_var} Over Time",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = histogram(
                    historical,
                    column=variable_to_field(explore_var),
                    title=f"{explore_var} Distribution",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Variable Relationships")
            scatter_x = st.selectbox(
                "X-axis",
                options=["Rainfall", "MaxTemp", "MinTemp"],
                index=0,
                key="scatter_x",
            )
            scatter_y = st.selectbox(
                "Y-axis",
                options=["Rainfall", "MaxTemp", "MinTemp"],
                index=1,
                key="scatter_y",
            )
            fig = scatter_plot(
                historical,
                x_col=variable_to_field(scatter_x),
                y_col=variable_to_field(scatter_y),
                title=f"{scatter_y} vs {scatter_x}",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for exploration")

    with tab3:
        st.subheader("Export Climate Data")

        historical = api.get_historical(location_id)
        forecasts = api.get_forecast(location_id, horizon=7)

        col1, col2 = st.columns(2)

        with col1:
            if historical:
                csv_hist = _df_to_csv(historical)
                st.download_button(
                    label="📥 Download Historical Data (CSV)",
                    data=csv_hist,
                    file_name=f"historical_{location_id}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No historical data to export")

        with col2:
            if forecasts:
                csv_forecast = _df_to_csv(forecasts)
                st.download_button(
                    label="📥 Download Forecast Data (CSV)",
                    data=csv_forecast,
                    file_name=f"forecast_{location_id}_7day.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No forecast data to export")

        st.divider()
        st.subheader("Download Charts as HTML")
        st.info(
            "Charts can be exported individually using the camera icon in Plotly toolbar (top-right of each chart)"
        )

    with tab4:
        st.subheader("Climate Report Generator")
        report_date = st.date_input("Report Date", value=datetime.now().date(), key="report_date")

        include_sections = st.multiselect(
            "Include Sections",
            options=[
                "Executive Summary",
                "District Analysis",
                "Forecast Outlook",
                "Risk Assessment",
                "Scenario Impact",
            ],
            default=["Executive Summary", "District Analysis"],
        )

        if st.button("📄 Generate Report", type="primary", use_container_width=True):
            st.success("Report generated successfully!")

            report_lines = [
                "# Climate Digital Twin — District Report",
                f"**Date:** {report_date}",
                f"**Districts:** {', '.join(districts)}",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]

            if "Executive Summary" in include_sections:
                report_lines.extend(
                    [
                        "## Executive Summary",
                        f"This report covers climate conditions for {', '.join(districts)}. "
                        f"The region shows typical seasonal patterns with monsoon influence "
                        f"from June to September.",
                        "",
                    ]
                )

            if "District Analysis" in include_sections:
                report_lines.append("## District Analysis")
                for d in districts:
                    summary = api.get_district_summary(d)
                    report_lines.append(
                        f"### {d}\n"
                        f"- Total Rainfall YTD: {summary.get('total_rainfall_ytd', 0):.1f} mm\n"
                        f"- Average Max Temp: {summary.get('avg_max_temp', 0):.1f} °C\n"
                        f"- Average Min Temp: {summary.get('avg_min_temp', 0):.1f} °C\n"
                        f"- Rainy Days: {summary.get('rainy_days', 0)}\n"
                        f"- Extreme Heat Days: {summary.get('extreme_heat_days', 0)}\n"
                        f"- Risk Level: {summary.get('risk_level', 'N/A')}\n"
                    )

            if "Forecast Outlook" in include_sections:
                report_lines.append("## Forecast Outlook")
                if forecasts:
                    for i, f in enumerate(forecasts):
                        report_lines.append(
                            f"- **Day {i + 1}:** Rainfall {f.get('rainfall', 0):.1f}mm, "
                            f"Max {f.get('max_temp', 0):.1f}°C, "
                            f"Min {f.get('min_temp', 0):.1f}°C "
                            f"(confidence: {f.get('prediction_confidence', 0):.2f})"
                        )
                else:
                    report_lines.append("No forecast data available.")
                report_lines.append("")

            if "Risk Assessment" in include_sections:
                report_lines.append("## Risk Assessment")
                for d in districts:
                    summary = api.get_district_summary(d)
                    report_lines.append(
                        f"- **{d}:** Risk Level = {summary.get('risk_level', 'N/A')}"
                    )
                report_lines.append("")

            if "Scenario Impact" in include_sections:
                report_lines.append("## Scenario Impact")
                report_lines.append(
                    "Scenario simulation results show potential impacts of "
                    "temperature changes and rainfall variations on district-level "
                    "climate conditions."
                )

            report_text = "\n".join(report_lines)

            st.markdown(report_text)
            st.download_button(
                label="📥 Download Report (Markdown)",
                data=report_text,
                file_name=f"climate_report_{report_date}.md",
                mime="text/markdown",
                use_container_width=True,
            )


def _df_to_csv(data: list[dict]) -> str:
    if not data:
        return ""
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
