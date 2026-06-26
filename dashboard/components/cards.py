"""Reusable metric and info card components for the dashboard."""

from __future__ import annotations

from typing import Any

import streamlit as st


def metric_card(
    label: str,
    value: str | float,
    delta: str | float | None = None,
    help_text: str | None = None,
) -> None:
    st.metric(label=label, value=value, delta=delta, help=help_text)


def info_card(title: str, content: str, icon: str = "ℹ️") -> None:
    st.markdown(
        f"""<div style="padding:1rem;border-radius:8px;background:#f0f2f6;margin:0.5rem 0">
        <strong>{icon} {title}</strong><br>{content}</div>""",
        unsafe_allow_html=True,
    )


def status_badge(label: str, status: str) -> None:
    colors = {"active": "#28a745", "inactive": "#dc3545", "pending": "#ffc107", "completed": "#17a2b8"}
    color = colors.get(status.lower(), "#6c757d")
    st.markdown(
        f"""<span style="background:{color};color:white;padding:0.2rem 0.6rem;
        border-radius:12px;font-size:0.8rem">{label}</span>""",
        unsafe_allow_html=True,
    )


def entity_detail_table(entity: dict[str, Any]) -> None:
    fields = [
        ("Location ID", entity.get("location_id", "")),
        ("District", entity.get("district", "")),
        ("Latitude", entity.get("latitude", "")),
        ("Longitude", entity.get("longitude", "")),
        ("Timestamp", entity.get("timestamp", "")),
        ("Rainfall (mm)", entity.get("rainfall", 0)),
        ("Max Temp (°C)", entity.get("max_temp", 0)),
        ("Min Temp (°C)", entity.get("min_temp", 0)),
        ("Risk Score", f"""{entity.get('risk_score', 0):.1f}"""),
        ("Confidence", f"""{entity.get('prediction_confidence', 0):.2f}"""),
        ("Data Source", entity.get("data_source", "")),
        ("State Type", entity.get("state_type", "")),
    ]
    md_rows = "\n".join(f"| **{k}** | {v} |" for k, v in fields)
    st.markdown(f"| Field | Value |\n| --- | --- |\n{md_rows}")
