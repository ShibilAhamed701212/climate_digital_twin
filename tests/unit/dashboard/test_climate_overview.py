"""Tests for dashboard/pages/01_climate_overview.py — render() function."""

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
    mock.get_current_state.return_value = {
        "location_id": "KA-BLR-001",
        "latitude": 12.97,
        "longitude": 77.59,
        "district": "Bengaluru Urban",
        "rainfall": 22.5,
        "max_temp": 32.0,
        "min_temp": 21.5,
        "risk_score": 15.0,
        "prediction_confidence": 0.75,
    }
    mock.get_historical.return_value = [
        {"timestamp": "2024-01-01", "rainfall": 10, "max_temp": 30, "min_temp": 20},
        {"timestamp": "2024-01-02", "rainfall": 15, "max_temp": 32, "min_temp": 22},
    ]
    return mock


def test_climate_overview_render_does_not_crash(api):
    m = __import__("dashboard.page_views.01_climate_overview", fromlist=["render"])

    m.render(api, {"variable": "Rainfall", "location_id": "KA-BLR-001"})
    assert True


def test_climate_overview_render_none_current(api):
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.01_climate_overview", fromlist=["render"])

    m.render(api, {"variable": "Rainfall", "location_id": "KA-BLR-001"})
    assert True


def test_climate_overview_render_empty_historical(api):
    api.get_historical.return_value = []
    m = __import__("dashboard.page_views.01_climate_overview", fromlist=["render"])

    m.render(api, {"variable": "MaxTemp", "location_id": "KA-MYS-001"})
    assert True


def test_climate_overview_render_no_state_for_all_locations(api):
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.01_climate_overview", fromlist=["render"])

    m.render(api, {"variable": "Rainfall", "location_id": "KA-BLR-001"})
    assert True
