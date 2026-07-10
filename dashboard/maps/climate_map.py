"""Folium map components for climate data visualization."""

from __future__ import annotations

from typing import Any

import folium
from folium.plugins import HeatMap

from dashboard.config.config import DEFAULT_CENTER, DEFAULT_ZOOM, TILE_STYLE, variable_to_field


def create_base_map(
    center: list[float] | None = None,
    zoom: int | None = None,
) -> folium.Map:
    return folium.Map(
        location=center or DEFAULT_CENTER,
        zoom_start=zoom or DEFAULT_ZOOM,
        tiles=TILE_STYLE,
        control_scale=True,
    )


def climate_overlay_map(
    locations: list[dict[str, Any]],
    variable: str = "Rainfall",
    center: list[float] | None = None,
    zoom: int | None = None,
) -> folium.Map:
    m = create_base_map(center, zoom)
    var_key = variable_to_field(variable)
    for loc in locations:
        value = loc.get(var_key, loc.get("rainfall", 0))
        color = _value_color(value, variable)
        folium.CircleMarker(
            location=[loc.get("latitude", 12.97), loc.get("longitude", 77.59)],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=_popup_html(loc, variable, value),
            tooltip=f"{loc.get('district', 'Unknown')}: {value:.1f}",
        ).add_to(m)
    return m


def district_boundary_map(
    locations: list[dict[str, Any]],
    variable: str = "Rainfall",
) -> folium.Map:
    m = create_base_map()
    var_key = variable_to_field(variable)
    for loc in locations:
        value = loc.get(var_key, loc.get("rainfall", 0))
        color = _value_color(value, variable)
        folium.CircleMarker(
            location=[loc.get("latitude", 12.97), loc.get("longitude", 77.59)],
            radius=15,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,
            popup=_popup_html(loc, variable, value),
            tooltip=loc.get("district", "Unknown"),
        ).add_to(m)
    return m


def risk_heatmap(
    locations: list[dict[str, Any]],
    risk_key: str = "composite_risk",
) -> folium.Map:
    m = create_base_map()
    heat_data = [
        [
            loc.get("latitude", 12.97),
            loc.get("longitude", 77.59),
            loc.get(risk_key, loc.get("risk_score", 0)),
        ]
        for loc in locations
    ]
    HeatMap(heat_data, radius=20, blur=15, max_zoom=10).add_to(m)
    return m


def forecast_map(
    current: dict[str, Any],
    forecasts: list[dict[str, Any]],
    variable: str = "Rainfall",
) -> folium.Map:
    m = create_base_map()
    var_key = variable_to_field(variable)
    c_val = current.get(var_key, current.get("rainfall", 0))
    c_color = _value_color(c_val, variable)
    folium.CircleMarker(
        location=[current.get("latitude", 12.97), current.get("longitude", 77.59)],
        radius=12,
        color=c_color,
        fill=True,
        fill_color=c_color,
        fill_opacity=0.8,
        popup=f"Current: {c_val:.1f}",
        tooltip="Current",
    ).add_to(m)
    for f in forecasts:
        f_val = f.get(var_key, f.get("rainfall", 0))
        f_color = _value_color(f_val, variable)
        folium.CircleMarker(
            location=[f.get("latitude", 12.97), f.get("longitude", 77.59)],
            radius=8,
            color=f_color,
            fill=True,
            fill_color=f_color,
            fill_opacity=0.5,
            popup=f"Forecast: {f_val:.1f}",
            tooltip=f.get("timestamp", "forecast"),
        ).add_to(m)
    return m


def _value_color(value: float, variable: str) -> str:
    if variable in ("Rainfall", "rainfall"):
        if value < 20:
            return "#b3d9ff"
        elif value < 60:
            return "#4da6ff"
        elif value < 100:
            return "#0066cc"
        else:
            return "#003366"
    else:
        if value < 20:
            return "#ffcccc"
        elif value < 30:
            return "#ff6666"
        elif value < 40:
            return "#cc0000"
        else:
            return "#660000"


def _popup_html(loc: dict[str, Any], variable: str, value: float) -> str:
    import html

    return f"""
    <b>{html.escape(str(loc.get("district", "Unknown")))}</b><br>
    <b>{html.escape(variable)}:</b> {value:.2f}<br>
    <b>Max Temp:</b> {html.escape(str(loc.get("max_temp", "N/A")))}°C<br>
    <b>Min Temp:</b> {html.escape(str(loc.get("min_temp", "N/A")))}°C<br>
    <b>Rainfall:</b> {html.escape(str(loc.get("rainfall", "N/A")))} mm<br>
    <b>Risk:</b> {html.escape(str(loc.get("risk_score", "N/A")))}
    """
