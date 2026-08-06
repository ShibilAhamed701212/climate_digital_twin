"""Page 9: Feedback — rating analytics, model comparison, location performance."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.config.config import SAMPLE_LOCATIONS


def render(api: Any, filters: dict) -> None:
    st.header("Feedback Analytics")
    st.markdown("Track model performance, rating trends, and location-specific feedback.")

    location_id = filters.get("location_id", SAMPLE_LOCATIONS[0]["id"])

    with st.expander("Submit feedback", expanded=False):
        fb_type = st.selectbox("Type", ["general", "forecast", "risk"], key="fb_type")
        fb_rating = st.slider("Rating", min_value=1, max_value=5, value=4, key="fb_rating")
        fb_comment = st.text_input("Comment", key="fb_comment")
        if st.button("Submit feedback", type="primary"):
            try:
                result = api.submit_feedback(
                    location_id=location_id,
                    rating=float(fb_rating),
                    feedback_type=fb_type,
                    comment=fb_comment,
                )
                st.success(f"Saved feedback {result.get('record_id', '')}")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not submit feedback: {exc}")

    try:
        feedback_data = api.get_feedback_data()
        df = pd.DataFrame(feedback_data) if feedback_data else pd.DataFrame()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("No feedback data available yet. Submit feedback above to populate analytics.")
        return

    st.subheader("Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", len(df))
    with col2:
        st.metric("Avg Rating", f"{df['rating'].mean():.2f}")
    with col3:
        st.metric("Rating Std", f"{df['rating'].std():.2f}" if len(df) > 1 else "0.00")
    with col4:
        st.metric("Locations", df["location"].nunique())

    st.subheader("Feedback Volume Over Time")

    volume_data = df.copy()
    volume_data["date"] = pd.to_datetime(volume_data["date"], errors="coerce")
    volume_by_date = (
        volume_data.dropna(subset=["date"])
        .groupby(volume_data["date"].dt.date)
        .size()
        .reset_index(name="count")
    )
    if not volume_by_date.empty:
        volume_by_date.columns = ["Date", "Count"]
        st.bar_chart(volume_by_date, x="Date", y="Count")

    st.subheader("Rating Distribution")

    rating_dist = df["rating"].round().astype(int).value_counts().reindex(range(1, 6), fill_value=0)
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
        rating_pct = (rating_dist / max(len(df), 1) * 100).round(1)
        dist_df = pd.DataFrame(
            {
                "Rating": [f"{i}" for i in range(1, 6)],
                "Count": rating_dist.values,
                "%": rating_pct.values,
            }
        )
        st.dataframe(dist_df, use_container_width=True, hide_index=True)

    st.subheader("Trend Analysis")

    df_sorted = df.copy()
    df_sorted["date"] = pd.to_datetime(df_sorted["date"], errors="coerce")
    df_sorted = df_sorted.sort_values("date")
    half = max(len(df_sorted) // 2, 1)
    first_half = df_sorted.iloc[:half]["rating"].mean()
    second_half = df_sorted.iloc[half:]["rating"].mean() if len(df_sorted) > half else first_half
    direction = "improving" if second_half > first_half else "declining"
    improvement = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("First Period Avg", f"{first_half:.2f}")
    tc2.metric("Recent Avg", f"{second_half:.2f}")
    tc3.metric("Trend", direction.title(), delta=f"{improvement:+.1f}%")

    if len(df_sorted) >= 2:
        df_sorted["rolling_avg"] = df_sorted["rating"].rolling(window=min(7, len(df_sorted))).mean()
        trend_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(df_sorted["date"]),
                "Rating": df_sorted["rating"],
                "7-Day Avg": df_sorted["rolling_avg"],
            }
        ).dropna(subset=["Date"])
        if not trend_df.empty:
            st.line_chart(trend_df, x="Date", y=["Rating", "7-Day Avg"])

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

    recent = df_sorted.sort_values("date", ascending=False).head(20)
    cols = [c for c in ["date", "location", "rating", "type"] if c in recent.columns]
    recent_display = recent[cols].copy()
    recent_display.columns = [c.title() for c in cols]
    st.dataframe(recent_display, use_container_width=True, hide_index=True)

    st.divider()
    st.caption(f"Feedback analytics updated at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
