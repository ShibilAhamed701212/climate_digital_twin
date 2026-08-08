"""Reusable metric and info card components for the dashboard."""

from __future__ import annotations

import html
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
        <strong>{html.escape(icon)} {html.escape(title)}</strong><br>{html.escape(content)}</div>""",
        unsafe_allow_html=True,
    )


def status_badge(label: str, status: str) -> None:
    colors = {
        "active": "#28a745",
        "inactive": "#dc3545",
        "pending": "#ffc107",
        "completed": "#17a2b8",
    }
    color = colors.get(status.lower(), "#6c757d")
    st.markdown(
        f"""<span style="background:{html.escape(color)};color:white;padding:0.2rem 0.6rem;
        border-radius:12px;font-size:0.8rem">{html.escape(label)}</span>""",
        unsafe_allow_html=True,
    )


def entity_detail_table(entity: dict[str, Any]) -> None:
    def _v(v: Any, unit: str = "") -> Any:
        if v is None or v == "":
            return "Unavailable"
        if isinstance(v, int | float):
            return f"{v:.1f} {unit}".strip()
        return v

    risk_score = entity.get("risk_score")
    fields = [
        ("Location ID", entity.get("location_id", "")),
        ("District", entity.get("district", "")),
        ("Latitude", entity.get("latitude", "")),
        ("Longitude", entity.get("longitude", "")),
        ("Timestamp", entity.get("timestamp", "")),
        ("Rainfall (mm)", _v(entity.get("rainfall"), "mm")),
        ("Max Temp (°C)", _v(entity.get("max_temp"), "°C")),
        ("Min Temp (°C)", _v(entity.get("min_temp"), "°C")),
        ("Risk Score", f"{risk_score:.1f}" if risk_score is not None else "Unavailable"),
        ("Confidence", f"""{entity.get("prediction_confidence", 0):.2f}"""),
        ("Data Source", entity.get("data_source", "")),
        ("State Type", entity.get("state_type", "")),
    ]
    md_rows = "\n".join(f"| **{k}** | {v} |" for k, v in fields)
    st.markdown(f"| Field | Value |\n| --- | --- |\n{md_rows}")
