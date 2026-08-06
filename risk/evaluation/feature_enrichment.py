"""Helpers to derive risk features from twin history and REAL observation CSVs."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REAL_FILES = (
    Path("data/real/training.csv"),
    Path("data/real/validation.csv"),
    Path("data/real/testing.csv"),
)


@lru_cache(maxsize=1)
def load_real_observation_frame() -> Any | None:
    """Load concatenated REAL Open-Meteo CSVs when present."""
    try:
        import pandas as pd
    except ImportError:
        return None

    frames = []
    for path in _REAL_FILES:
        if path.exists():
            try:
                frames.append(pd.read_csv(path, parse_dates=["Date"]))
            except Exception as exc:
                logger.debug("Failed reading %s: %s", path, exc)
    if not frames:
        return None
    import pandas as pd

    return pd.concat(frames, ignore_index=True).sort_values("Date")


def climatology_from_real_csv(
    latitude: float | None = None,
    longitude: float | None = None,
    lat_tol: float = 0.2,
    lon_tol: float = 0.2,
) -> dict[str, float]:
    """Return daily mean rainfall/temp from REAL CSVs nearest to coordinates."""
    df = load_real_observation_frame()
    if df is None or df.empty:
        return {}

    subset = df
    if latitude is not None and longitude is not None and "Latitude" in df.columns:
        subset = df[
            ((df["Latitude"] - latitude).abs() <= lat_tol)
            & ((df["Longitude"] - longitude).abs() <= lon_tol)
        ]
        if subset.empty:
            subset = df

    out: dict[str, float] = {}
    if "Rainfall" in subset.columns and len(subset):
        out["mean_rainfall"] = float(subset["Rainfall"].mean())
        out["p50_rainfall"] = float(subset["Rainfall"].median())
    if "MaxTemp" in subset.columns and len(subset):
        out["mean_max_temp"] = float(subset["MaxTemp"].mean())
        out["p50_max_temp"] = float(subset["MaxTemp"].median())
    if "MinTemp" in subset.columns and len(subset):
        out["mean_min_temp"] = float(subset["MinTemp"].mean())
    out["sample_count"] = float(len(subset))
    return out


def derive_series_features(
    rainfall_series: list[float],
    max_temp_series: list[float],
    *,
    rain_dry_threshold_mm: float = 1.0,
    hot_day_threshold_c: float = 35.0,
    accumulation_window: int = 3,
) -> dict[str, float | int]:
    """Derive dry-spell / hot-spell / accumulation features from ordered history."""
    rains = [float(x) for x in rainfall_series if x is not None]
    temps = [float(x) for x in max_temp_series if x is not None]

    dry_period_days = 0
    for rain in reversed(rains):
        if rain < rain_dry_threshold_mm:
            dry_period_days += 1
        else:
            break

    consecutive_hot_days = 0
    for temp in reversed(temps):
        if temp >= hot_day_threshold_c:
            consecutive_hot_days += 1
        else:
            break

    window = rains[-accumulation_window:] if rains else []
    multi_day_accumulation = float(sum(window)) if window else 0.0
    mean_rain = float(sum(rains) / len(rains)) if rains else None
    mean_temp = float(sum(temps) / len(temps)) if temps else None
    latest_temp = temps[-1] if temps else None
    seasonal_anomaly = (
        float(latest_temp - mean_temp) if latest_temp is not None and mean_temp is not None else 0.0
    )

    return {
        "dry_period_days": dry_period_days,
        "consecutive_hot_days": consecutive_hot_days,
        "multi_day_accumulation": multi_day_accumulation,
        "mean_rainfall": mean_rain if mean_rain is not None else 0.0,
        "mean_max_temp": mean_temp if mean_temp is not None else 0.0,
        "seasonal_anomaly": seasonal_anomaly,
        "history_len": len(rains),
    }
