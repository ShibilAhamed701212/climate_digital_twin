"""Side-by-side comparison chart components."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.config.config import variable_to_field


def before_after_chart(
    before: dict[str, Any],
    after: dict[str, Any],
    variable: str = "Rainfall",
) -> go.Figure:
    labels = ["Before", "After"]
    var_key = variable_to_field(variable)
    before_val = before.get(var_key, before.get("rainfall", 0))
    after_val = after.get(var_key, after.get("rainfall", 0))
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=[before_val, after_val],
            marker_color=["#3498db", "#e74c3c"],
            text=[f"{before_val:.1f}", f"{after_val:.1f}"],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"{variable} — Before vs After",
        yaxis_title=variable,
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return fig


def comparison_bar(
    data: list[dict[str, Any]],
    x_key: str = "district",
    y_key: str = "rainfall",
    title: str = "District Comparison",
    color_col: str | None = None,
) -> go.Figure:
    df = _to_df(data)
    fig = px.bar(
        df,
        x=x_key,
        y=y_key,
        title=title,
        color=color_col,
        labels={y_key: y_key},
        text_auto=".1f",
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=60),
        height=400,
        xaxis_tickangle=-45,
    )
    return fig


def grouped_comparison(
    data: list[dict[str, Any]],
    x_key: str = "district",
    y_keys: list[str] | None = None,
    title: str = "Multi-Variable Comparison",
) -> go.Figure:
    if y_keys is None:
        y_keys = ["rainfall", "max_temp", "min_temp"]
    df = _to_df(data)
    fig = go.Figure()
    for key in y_keys:
        fig.add_trace(
            go.Bar(
                name=key,
                x=df[x_key],
                y=df[key],
            )
        )
    fig.update_layout(
        title=title,
        barmode="group",
        margin=dict(l=20, r=20, t=40, b=60),
        height=400,
        xaxis_tickangle=-45,
    )
    return fig


def _to_df(data: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(data)
