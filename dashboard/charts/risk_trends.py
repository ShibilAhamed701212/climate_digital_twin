"""Risk trend and SHAP explanation chart components."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def risk_trend_chart(
    risk_data: dict[str, Any],
    title: str = "Risk Score Trend",
) -> go.Figure:
    trend = risk_data.get("trend", [])
    months = [f"M{i + 1}" for i in range(len(trend))]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=trend,
            mode="lines+markers",
            name="Risk Score",
            line=dict(color="#e74c3c", width=2),
            fill="tozeroy",
            fillcolor="rgba(231,76,60,0.1)",
        )
    )
    fig.update_layout(
        title=title,
        yaxis_title="Risk Score",
        yaxis_range=[0, 100],
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return fig


def risk_gauge(value: float, title: str = "Composite Risk") -> go.Figure:
    color = "green" if value < 30 else "orange" if value < 60 else "red"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            title={"text": title},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 30], "color": "lightgreen"},
                    {"range": [30, 60], "color": "lightyellow"},
                    {"range": [60, 100], "color": "lightcoral"},
                ],
            },
        )
    )
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def shap_waterfall(shap_values: dict[str, float]) -> go.Figure:
    features = list(shap_values.keys())
    values = list(shap_values.values())
    colors = ["#e74c3c" if v > 0 else "#3498db" for v in values]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=features,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.3f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="SHAP Feature Importance",
        xaxis_title="SHAP Value",
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,
    )
    return fig


def risk_category_chart(risk_data: dict[str, Any]) -> go.Figure:
    categories = ["Heat Risk", "Heavy Rain Risk", "Dryness Risk"]
    values = [
        risk_data.get("heat_risk", 0),
        risk_data.get("flood_risk", 0),
        risk_data.get("drought_risk", 0),
    ]
    fig = go.Figure(
        go.Bar(
            x=categories,
            y=values,
            marker_color=["#e74c3c", "#3498db", "#f39c12"],
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Risk Breakdown by Category",
        yaxis_title="Risk Score",
        yaxis_range=[0, 100],
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return fig
