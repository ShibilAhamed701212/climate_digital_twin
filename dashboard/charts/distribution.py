"""Distribution and histogram chart components."""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go


def histogram(
    data: list[dict[str, Any]],
    column: str = "rainfall",
    title: str = "Distribution",
    nbins: int = 20,
) -> go.Figure:
    df = _to_df(data)
    fig = px.histogram(
        df,
        x=column,
        nbins=nbins,
        title=title,
        marginal="box",
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=350,
    )
    return fig


def scatter_plot(
    data: list[dict[str, Any]],
    x_col: str = "max_temp",
    y_col: str = "rainfall",
    color_col: str | None = None,
    title: str = "Variable Relationship",
) -> go.Figure:
    df = _to_df(data)
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        trendline="ols",
        labels={x_col: x_col, y_col: y_col},
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
    )
    return fig


def _to_df(data: list[dict[str, Any]]) -> pd.DataFrame:  # noqa: F821
    import pandas as pd
    return pd.DataFrame(data)
