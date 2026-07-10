"""Tests for dashboard/pages/03_twin_state.py — render() function."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def api():
    mock = MagicMock()
    mock.get_all_locations.return_value = [
        {"id": "KA-BLR-001", "lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
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
        "timestamp": "2024-01-01",
        "state_type": "current",
        "data_source": "api",
    }
    mock.get_historical.return_value = [
        {
            "timestamp": "2024-01-01",
            "rainfall": 10,
            "max_temp": 30,
            "min_temp": 22,
            "state_type": "historical",
        },
        {
            "timestamp": "2024-01-02",
            "rainfall": 15,
            "max_temp": 32,
            "min_temp": 21,
            "state_type": "historical",
        },
    ]
    mock.get_forecast.return_value = [
        {"rainfall": 10.0, "max_temp": 30.0, "min_temp": 22.0, "prediction_confidence": 0.85},
        {"rainfall": 8.0, "max_temp": 32.0, "min_temp": 21.0, "prediction_confidence": 0.75},
        {"rainfall": 5.0, "max_temp": 34.0, "min_temp": 20.0, "prediction_confidence": 0.65},
    ]
    return mock


def test_twin_state_render_does_not_crash(api):
    m = __import__("dashboard.page_views.03_twin_state", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True


def test_twin_state_no_current(api):
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.03_twin_state", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True


def test_twin_state_no_historical(api):
    api.get_historical.return_value = []
    m = __import__("dashboard.page_views.03_twin_state", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True


def test_twin_state_no_forecast(api):
    api.get_forecast.return_value = []
    m = __import__("dashboard.page_views.03_twin_state", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "MaxTemp"})
    assert True


def test_twin_state_no_current_data_for_all_locations(api):
    api.get_all_locations.return_value = [
        {"id": "KA-BLR-001", "lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
    ]
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.03_twin_state", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True
