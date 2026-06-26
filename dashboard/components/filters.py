"""Reusable filter widgets for dashboard pages."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def date_range_filter(
    key: str = "date_range",
    default_days: int = 90,
) -> tuple[date, date]:
    today = date.today()
    default_start = today - timedelta(days=default_days)
    start = st.date_input("Start Date", value=default_start, key=f"{key}_start")
    end = st.date_input("End Date", value=today, key=f"{key}_end")
    return start, end


def horizon_selector(key: str = "horizon") -> int:
    options = {"1 Day": 1, "3 Days": 3, "7 Days": 7}
    label = st.selectbox("Forecast Horizon", options=list(options.keys()), index=1, key=key)
    return options[label]


def scenario_parameters() -> dict[str, float]:
    col1, col2 = st.columns(2)
    with col1:
        temp_delta = st.slider(
            "Temperature Delta (°C)", min_value=-5.0, max_value=5.0, value=0.0, step=0.5
        )
    with col2:
        rain_change = st.slider(
            "Rainfall Change (%)", min_value=-100, max_value=200, value=0, step=10
        )
    return {"temperature_delta": temp_delta, "rainfall_change_pct": rain_change}
