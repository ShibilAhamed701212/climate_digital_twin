"""Before/after and delta comparison map components."""

from __future__ import annotations

from typing import Any

import folium

from dashboard.config.config import DEFAULT_CENTER, variable_to_field
from dashboard.maps.climate_map import create_base_map


def before_after_comparison(
    before: dict[str, Any],
    after: dict[str, Any],
    variable: str = "Rainfall",
) -> folium.Map:
    m = create_base_map()
    var_key = variable_to_field(variable)
    b_val = before.get(var_key, before.get("rainfall", 0))
    a_val = after.get(var_key, after.get("rainfall", 0))
    lat = before.get("latitude", DEFAULT_CENTER[0])
    lon = before.get("longitude", DEFAULT_CENTER[1])

    b_color = _delta_color(b_val, a_val, variable)
    a_color = _delta_color(a_val, b_val, variable)

    folium.CircleMarker(
        location=[lat, lon],
        radius=15,
        color=b_color,
        fill=True,
        fill_color=b_color,
        fill_opacity=0.6,
        popup=f"Before: {b_val:.1f}",
        tooltip="Before",
    ).add_to(m)

    offset_lon = lon + 0.05
    folium.CircleMarker(
        location=[lat, offset_lon],
        radius=15,
        color=a_color,
        fill=True,
        fill_color=a_color,
        fill_opacity=0.6,
        popup=f"After: {a_val:.1f}",
        tooltip="After",
    ).add_to(m)

    folium.PolyLine(
        locations=[[lat, lon], [lat, offset_lon]],
        color="gray",
        weight=2,
        dash_array="5, 5",
    ).add_to(m)

    return m


def delta_map(
    before: dict[str, Any],
    after: dict[str, Any],
    variable: str = "Rainfall",
) -> folium.Map:
    m = create_base_map()
    var_key = variable_to_field(variable)
    b_val = before.get(var_key, before.get("rainfall", 0))
    a_val = after.get(var_key, after.get("rainfall", 0))
    delta = a_val - b_val
    lat = before.get("latitude", DEFAULT_CENTER[0])
    lon = before.get("longitude", DEFAULT_CENTER[1])

    d_color = "green" if abs(delta) < 5 else "orange" if abs(delta) < 20 else "red"
    arrow_dir = "▲" if delta > 0 else "▼"

    folium.CircleMarker(
        location=[lat, lon],
        radius=18,
        color=d_color,
        fill=True,
        fill_color=d_color,
        fill_opacity=0.7,
        popup=f"{arrow_dir} Delta: {delta:+.1f}",
        tooltip=f"{variable} Change: {delta:+.1f}",
    ).add_to(m)

    return m


def _delta_color(value: float, other: float, variable: str) -> str:
    delta = value - other
    if variable in ("Rainfall", "rainfall"):
        if delta > 0:
            return "#0066cc"
        else:
            return "#ff9933"
    else:
        if delta > 0:
            return "#cc0000"
        else:
            return "#0066cc"
