"""Time series Plotly chart components."""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go


def line_chart(
    data: list[dict[str, Any]],
    x_key: str = "timestamp",
    y_key: str = "rainfall",
    title: str = "Time Series",
    color: str | None = None,
    y_label: str | None = None,
) -> go.Figure:
    df = _to_df(data)
    fig = px.line(
        df,
        x=x_key,
        y=y_key,
        title=title,
        color=color,
        labels={y_key: y_label or y_key},
        markers=True,
    )
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
    )
    return fig


def multi_line_chart(
    data: list[dict[str, Any]],
    x_key: str = "timestamp",
    y_keys: list[str] | None = None,
    title: str = "Multi-Variable Time Series",
) -> go.Figure:
    if y_keys is None:
        y_keys = ["rainfall", "max_temp", "min_temp"]
    df = _to_df(data)
    fig = go.Figure()
    for key in y_keys:
        fig.add_trace(go.Scatter(
            x=df[x_key],
            y=df[key],
            mode="lines+markers",
            name=key,
        ))
    fig.update_layout(
        title=title,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
    )
    return fig


def confidence_band_chart(
    data: list[dict[str, Any]],
    x_key: str = "timestamp",
    y_key: str = "rainfall",
    confidence_key: str = "prediction_confidence",
    title: str = "Forecast with Confidence",
) -> go.Figure:
    df = _to_df(data)
    values = df[y_key]
    conf = df[confidence_key].fillna(0.5)
    upper = values * (1 + (1 - conf))
    lower = values * conf

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_key],
        y=upper,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        name="Upper Bound",
    ))
    fig.add_trace(go.Scatter(
        x=df[x_key],
        y=lower,
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(0,100,200,0.2)",
        line=dict(width=0),
        showlegend=False,
        name="Confidence Band",
    ))
    fig.add_trace(go.Scatter(
        x=df[x_key],
        y=values,
        mode="lines+markers",
        name=y_key,
        line=dict(color="royalblue", width=2),
    ))
    fig.update_layout(
        title=title,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
    )
    return fig


def _to_df(data: list[dict[str, Any]]) -> pd.DataFrame:  # noqa: F821
    import pandas as pd
    return pd.DataFrame(data)
