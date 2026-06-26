"""NASA POWER API client for fetching historical daily climate data.

Provides grid-based retrieval of precipitation and temperature data
with concurrent API calls and synthetic fallback when offline.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

NASA_PARAM_MAP: dict[str, str] = {
    "rainfall": "PRECTOTCORR",
    "max_temp": "T2M_MAX",
    "min_temp": "T2M_MIN",
}

COLUMN_MAP: dict[str, str] = {
    "rainfall": "Rainfall",
    "max_temp": "MaxTemp",
    "min_temp": "MinTemp",
}


def generate_grid(resolution: float, bounds: dict[str, float]) -> list[dict[str, float]]:
    """Generate a regular lat/lon grid within bounds."""
    lats = np.arange(bounds["min_lat"], bounds["max_lat"] + resolution, resolution)
    lons = np.arange(bounds["min_lon"], bounds["max_lon"] + resolution, resolution)
    points: list[dict[str, float]] = []
    for lat in lats:
        for lon in lons:
            points.append({"latitude": round(float(lat), 4), "longitude": round(float(lon), 4)})
    return points


def fetch_point(
    lat: float, lon: float, start_date: str, end_date: str, source_config: dict[str, Any]
) -> dict[str, Any] | None:
    """Fetch daily climate data for a single lat/lon point from NASA POWER."""
    params: dict[str, Any] = {
        "parameters": ",".join(source_config.get("parameters", NASA_PARAM_MAP).values()),
        "community": source_config.get("community", "RE"),
        "format": source_config.get("format", "JSON"),
        "start": start_date,
        "end": end_date,
        "latitude": lat,
        "longitude": lon,
    }
    url = source_config.get("endpoint", NASA_POWER_URL)
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        logger.warning("NASA POWER request failed for lat=%.4f lon=%.4f", lat, lon, exc_info=True)
        return None


def parse_response(
    data: dict[str, Any] | None, lat: float, lon: float, source_config: dict[str, Any]
) -> dict[str, pd.DataFrame] | None:
    """Parse NASA POWER JSON response into per-dataset DataFrames."""
    if data is None:
        return None
    try:
        params = data["properties"]["parameter"]
        param_map = source_config.get("parameters", NASA_PARAM_MAP)
        reversed_map = {v: k for k, v in param_map.items()}
        param_keys = list(param_map.values())
        date_keys_set: set[str] = set()
        for pk in param_keys:
            if pk in params:
                date_keys_set.update(params[pk].keys())
        if not date_keys_set:
            return None
        date_keys = sorted(date_keys_set)

        all_records: dict[str, list[dict[str, Any]]] = {k: [] for k in param_map}
        for date_str in date_keys:
            dt = datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            for nasa_key, ds_key in reversed_map.items():
                raw = params.get(nasa_key, {}).get(date_str)
                if raw is not None:
                    col_name = COLUMN_MAP.get(ds_key, ds_key)
                    all_records[ds_key].append({
                        "Date": dt,
                        "Latitude": lat,
                        "Longitude": lon,
                        col_name: float(raw),
                    })
        result: dict[str, pd.DataFrame] = {}
        for ds_key in param_map:
            if all_records[ds_key]:
                result[ds_key] = pd.DataFrame(all_records[ds_key])
        return result
    except (KeyError, ValueError, TypeError):
        logger.warning("Failed to parse NASA POWER response for lat=%.4f lon=%.4f", lat, lon, exc_info=True)
        return None


def fetch_nasa_power_grid(
    bounds: dict[str, float],
    start_date: datetime,
    end_date: datetime,
    source_config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    """Fetch daily climate data from NASA POWER for all grid points.

    Returns dict with keys 'rainfall', 'max_temp', 'min_temp' containing
    DataFrames matching the expected pipeline format (Date, Latitude, Longitude, <ValueCol>).
    """
    resolution = source_config.get("resolution", 1.0)
    points = generate_grid(resolution, bounds)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    max_workers = source_config.get("max_workers", 4)

    logger.info("NASA POWER: fetching %d grid points (resolution=%.2f°)", len(points), resolution)

    param_map = source_config.get("parameters", NASA_PARAM_MAP)
    all_records: dict[str, list[pd.DataFrame]] = {k: [] for k in param_map}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_point, p["latitude"], p["longitude"], start_str, end_str, source_config): p
            for p in points
        }
        for future in as_completed(future_map):
            point = future_map[future]
            try:
                data = future.result()
                parsed = parse_response(data, point["latitude"], point["longitude"], source_config)
                if parsed:
                    for key in param_map:
                        if key in parsed and not parsed[key].empty:
                            all_records[key].append(parsed[key])
                else:
                    logger.debug("No NASA POWER data for lat=%.4f lon=%.4f", point["latitude"], point["longitude"])
            except Exception:
                logger.error("Failed to process NASA POWER point lat=%.4f lon=%.4f", point["latitude"], point["longitude"], exc_info=True)

    result: dict[str, pd.DataFrame] = {}
    for key in param_map:
        if all_records[key]:
            result[key] = pd.concat(all_records[key], ignore_index=True)
            logger.info("NASA POWER %s: %d records from %d points", key, len(result[key]), len(points))
        else:
            logger.warning("NASA POWER returned no data for %s", key)
    return result
