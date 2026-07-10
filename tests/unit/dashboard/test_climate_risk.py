"""Tests for dashboard/pages/05_climate_risk.py — render() function."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def api():
    mock = MagicMock()
    mock.get_all_locations.return_value = [
        {"id": "KA-BLR-001", "lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
        {"id": "KA-MYS-001", "lat": 12.30, "lon": 76.65, "district": "Mysuru"},
    ]
    mock.get_risk.return_value = {
        "location_id": "KA-BLR-001",
        "district": "Bengaluru Urban",
        "latitude": 12.97,
        "longitude": 77.59,
        "composite_risk": 25.0,
        "heat_risk": 32.0,
        "flood_risk": 18.0,
        "drought_risk": 14.0,
        "category": "Moderate",
        "trend": [25.0, 27.0, 24.0, 26.0],
        "shap_summary": {"Rainfall": 0.5, "MaxTemp": 0.75, "MinTemp": 0.25},
    }
    mock.get_current_state.return_value = {
        "location_id": "KA-BLR-001",
        "rainfall": 22.5,
        "max_temp": 32.0,
        "min_temp": 21.5,
    }
    return mock


def test_climate_risk_render_does_not_crash(api):
    m = __import__("dashboard.page_views.05_climate_risk", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001"})
    assert True


def test_climate_risk_no_risk_data(api):
    api.get_risk.return_value = None
    m = __import__("dashboard.page_views.05_climate_risk", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001"})
    assert True


def test_climate_risk_no_current(api):
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.05_climate_risk", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001"})
    assert True


def test_climate_risk_no_shap(api):
    api.get_risk.return_value = {
        "location_id": "KA-BLR-001",
        "district": "Bengaluru Urban",
        "latitude": 12.97,
        "longitude": 77.59,
        "composite_risk": 25.0,
        "heat_risk": 32.0,
        "flood_risk": 18.0,
        "drought_risk": 14.0,
        "category": "Moderate",
        "trend": [25.0],
    }
    m = __import__("dashboard.page_views.05_climate_risk", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001"})
    assert True


def test_climate_risk_no_risk_data_list(api):
    api.get_all_locations.return_value = []
    m = __import__("dashboard.page_views.05_climate_risk", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001"})
    assert True
