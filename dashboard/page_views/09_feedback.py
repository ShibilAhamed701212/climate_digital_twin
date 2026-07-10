"""Page 9: Feedback — rating analytics, model comparison, location performance."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st


def _generate_sample_feedback_data() -> pd.DataFrame:
    np.random.seed(42)
    PILOT_DISTRICTS = ["mumbai", "delhi", "chennai", "kolkata", "hyderabad", "bengaluru"]  # noqa: N806
    records = []
    for _i in range(100):
        from datetime import timedelta

        ts = datetime.now(UTC) - timedelta(days=np.random.randint(0, 90))
        records.append(
            {
                "date": ts.date().isoformat(),
                "rating": int(np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.1, 0.2, 0.35, 0.3])),
                "location": np.random.choice(PILOT_DISTRICTS),
                "type": np.random.choice(["risk", "forecast", "general"]),
            }
        )
    return pd.DataFrame(records)


def render(api: Any, filters: dict) -> None:  # noqa: ARG001
    st.header("Feedback Analytics")
    st.markdown("Track model performance, rating trends, and location-specific feedback.")

    df = _generate_sample_feedback_data()

    st.subheader("Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", len(df))
    with col2:
        st.metric("Avg Rating", f"{df['rating'].mean():.2f}")
    with col3:
        st.metric("Rating Std", f"{df['rating'].std():.2f}")
    with col4:
        st.metric("Locations", df["location"].nunique())

    st.subheader("Feedback Volume Over Time")

    volume_data = df.copy()
    volume_data["date"] = pd.to_datetime(volume_data["date"])
    volume_by_date = (
        volume_data.groupby(volume_data["date"].dt.date).size().reset_index(name="count")
    )
    volume_by_date.columns = ["Date", "Count"]
    st.bar_chart(volume_by_date, x="Date", y="Count")

    st.subheader("Rating Distribution")

    rating_dist = df["rating"].value_counts().sort_index()
    rating_df = pd.DataFrame(
        {
            "Rating": rating_dist.index,
            "Count": rating_dist.values,
        }
    )
    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.bar_chart(rating_df, x="Rating", y="Count")
    with col_table:
        rating_pct = (rating_dist / len(df) * 100).round(1)
        dist_df = pd.DataFrame(
            {
                "Rating": [f"{i}" for i in range(1, 6)],
                "Count": rating_dist.values,
                "%": rating_pct.values,
            }
        )
        st.dataframe(dist_df, use_container_width=True, hide_index=True)

    st.subheader("Trend Analysis")

    df_sorted = df.sort_values("date")
    half = len(df_sorted) // 2
    first_half = df_sorted.iloc[:half]["rating"].mean()
    second_half = df_sorted.iloc[half:]["rating"].mean()
    direction = "improving" if second_half > first_half else "declining"
    improvement = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("First Period Avg", f"{first_half:.2f}")
    tc2.metric("Recent Avg", f"{second_half:.2f}")
    tc3.metric("Trend", direction.title(), delta=f"{improvement:+.1f}%")

    df_sorted = df.sort_values("date")
    df_sorted["rolling_avg"] = df_sorted["rating"].rolling(window=7).mean()
    trend_df = pd.DataFrame(
        {
            "Date": pd.to_datetime(df_sorted["date"]),
            "Rating": df_sorted["rating"],
            "7-Day Avg": df_sorted["rolling_avg"],
        }
    )
    st.line_chart(trend_df, x="Date", y=["Rating", "7-Day Avg"])

    st.subheader("Model Performance Comparison")

    model_data = {
        "Model": ["Flood", "Heat", "Drought", "Composite"],
        "Avg Rating": [4.2, 3.8, 4.0, 3.9],
        "Feedback Count": [45, 38, 42, 50],
        "Accuracy": [0.88, 0.82, 0.85, 0.86],
    }
    model_df = pd.DataFrame(model_data)
    model_df["Accuracy %"] = (model_df["Accuracy"] * 100).round(1)
    st.dataframe(model_df, use_container_width=True, hide_index=True)

    st.subheader("Location Performance Scores")

    loc_perf = (
        df.groupby("location")
        .agg(
            avg_rating=("rating", "mean"),
            count=("rating", "count"),
        )
        .reset_index()
    )

    loc_perf["avg_rating"] = loc_perf["avg_rating"].round(2)
    loc_perf.columns = ["Location", "Avg Rating", "Count"]
    loc_perf = loc_perf.sort_values("Avg Rating", ascending=False)

    col_loc1, col_loc2 = st.columns([1, 1])
    with col_loc1:
        st.dataframe(loc_perf, use_container_width=True, hide_index=True)
    with col_loc2:
        st.bar_chart(loc_perf, x="Location", y="Avg Rating")

    st.subheader("Recent Feedback Entries")

    recent = df.sort_values("date", ascending=False).head(20)
    recent_display = recent[["date", "location", "rating", "type"]].copy()
    recent_display.columns = ["Date", "Location", "Rating", "Type"]
    st.dataframe(recent_display, use_container_width=True, hide_index=True)

    st.divider()
    st.caption(f"Feedback analytics updated at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
