"""Data source indicator — displays provenance metadata on dashboard widgets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st


STATUS_LABELS = {
    "LIVE": ("🟢", "Live"),
    "CACHED": ("🟡", "Cached"),
    "HISTORICAL": ("🔵", "Historical"),
    "UNAVAILABLE": ("⚪", "Unavailable"),
}

STATUS_HELP = {
    "LIVE": "Fresh observation from a live provider",
    "CACHED": "Previously downloaded observation within cache window",
    "HISTORICAL": "Bundled archived dataset (NASA POWER 1981-2023)",
    "UNAVAILABLE": "No verified observation exists",
}


def data_source_indicator(observation: dict[str, Any] | None) -> None:
    """Render a compact provenance badge for a data observation.

    Call this next to every chart, map, KPI, or card that displays
    climate data.
    """
    if observation is None:
        st.caption("⚪ Unavailable | No data")
        return

    status = observation.get("status", "UNAVAILABLE")
    icon, label = STATUS_LABELS.get(status, ("⚪", "Unknown"))
    provider = observation.get("provider", "unknown")
    obs_ts = observation.get("observation_timestamp", "")
    age = observation.get("age_seconds", 0)

    help_text = STATUS_HELP.get(status, "")
    parts = [f"{icon} {label}"]
    if provider:
        parts.append(provider)
    if obs_ts:
        parts.append(str(obs_ts)[:10])
    if age:
        age_str = _format_age(age)
        parts.append(age_str)

    st.caption(" | ".join(parts), help=help_text)


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    else:
        return f"{int(seconds / 86400)}d ago"
