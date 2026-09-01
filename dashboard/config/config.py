"""Dashboard configuration — externalized settings for the Streamlit dashboard."""

from __future__ import annotations

import os
from typing import Any

import yaml

_CONFIG_CACHE: dict[str, Any] | None = None


def _load_data_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    with open("config/data_config.yaml") as f:
        _CONFIG_CACHE = yaml.safe_load(f)
    return _CONFIG_CACHE


DASHBOARD_TITLE = "Climate Digital Twin — Karnataka"
DASHBOARD_ICON = "🌍"
PAGE_ICON = "🌤"

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
COPILOT_API_URL = os.environ.get("COPILOT_API_URL", "http://localhost:8005")
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "30"))
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8004")

KARNATAKA_BOUNDS = {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}

DEFAULT_CENTER = [15.0, 76.0]
DEFAULT_ZOOM = 7
TILE_STYLE = "OpenStreetMap"

COLOR_SCHEMES = {
    "Rainfall": "Blues",
    "MaxTemp": "Reds",
    "MinTemp": "Oranges",
    "Risk": "RdYlGn_r",
}

VARIABLE_UNITS = {
    "Rainfall": "mm",
    "MaxTemp": "°C",
    "MinTemp": "°C",
}

VARIABLE_LABELS = {
    "Rainfall": "Rainfall (mm)",
    "MaxTemp": "Max Temperature (°C)",
    "MinTemp": "Min Temperature (°C)",
}

VARIABLE_TO_FIELD = {
    "Rainfall": "rainfall",
    "MaxTemp": "max_temp",
    "MinTemp": "min_temp",
}


def variable_to_field(variable: str) -> str:
    return VARIABLE_TO_FIELD.get(variable, variable.lower())


PAGE_CONFIG = {
    "page_title": DASHBOARD_TITLE,
    "page_icon": PAGE_ICON,
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

PAGES = [
    {"title": "Climate Overview", "file": "01_climate_overview", "icon": "🌍"},
    {"title": "Forecast Viewer", "file": "02_forecast_viewer", "icon": "📈"},
    {"title": "Digital Twin State", "file": "03_twin_state", "icon": "🔄"},
    {"title": "Scenario Simulator", "file": "04_scenario_simulator", "icon": "🔮"},
    {"title": "Climate Risk", "file": "05_climate_risk", "icon": "⚠️"},
    {"title": "Reports & Insights", "file": "06_reports", "icon": "📊"},
    {"title": "AI Copilot", "file": "07_copilot_chat", "icon": "🤖"},
    {"title": "Knowledge Base", "file": "08_knowledge_base", "icon": "📚"},
    {"title": "Spatial Grid", "file": "09_spatial_grid", "icon": "🗺️"},
    {"title": "Feedback", "file": "10_feedback", "icon": "💬"},
    {"title": "Disaster Intelligence", "file": "11_disaster_intelligence", "icon": "🛰️"},
]

HORIZONS = {"1-Day": 1, "3-Day": 3, "7-Day": 7}

PILOT_DISTRICTS = [
    "Bengaluru Urban",
    "Mysuru",
    "Belagavi",
    "Dakshina Kannada",
    "Kalaburagi",
]

SAMPLE_LOCATIONS = [
    {"id": "KA-BLR-001", "lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
    {"id": "KA-MYS-001", "lat": 12.30, "lon": 76.65, "district": "Mysuru"},
    {"id": "KA-BEL-001", "lat": 15.85, "lon": 74.50, "district": "Belagavi"},
    {"id": "KA-MNG-001", "lat": 12.87, "lon": 74.88, "district": "Dakshina Kannada"},
    {"id": "KA-GUL-001", "lat": 17.33, "lon": 76.83, "district": "Kalaburagi"},
    {"id": "KA-UDP-001", "lat": 13.34, "lon": 74.75, "district": "Udupi"},
    {"id": "KA-SHM-001", "lat": 13.42, "lon": 75.25, "district": "Shivamogga"},
    {"id": "KA-HBL-001", "lat": 15.49, "lon": 75.01, "district": "Dharwad"},
    {"id": "KA-HAS-001", "lat": 13.01, "lon": 76.10, "district": "Hassan"},
    {"id": "KA-TUM-001", "lat": 13.34, "lon": 77.10, "district": "Tumakuru"},
]
