"""Tests for dashboard/pages/02_forecast_viewer.py — render() function."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def api():
    mock = MagicMock()
    mock.get_current_state.return_value = {
        "location_id": "KA-BLR-001",
        "latitude": 12.97,
        "longitude": 77.59,
        "rainfall": 22.5,
        "max_temp": 32.0,
        "min_temp": 21.5,
        "prediction_confidence": 0.75,
    }
    mock.get_forecast.return_value = [
        {
            "location_id": "KA-BLR-001",
            "latitude": 12.97,
            "longitude": 77.59,
            "rainfall": 10.0,
            "max_temp": 30.0,
            "min_temp": 22.0,
            "prediction_confidence": 0.85,
            "timestamp": "2024-01-02",
        },
        {
            "location_id": "KA-BLR-001",
            "latitude": 12.97,
            "longitude": 77.59,
            "rainfall": 8.0,
            "max_temp": 32.0,
            "min_temp": 21.0,
            "prediction_confidence": 0.75,
            "timestamp": "2024-01-03",
        },
        {
            "location_id": "KA-BLR-001",
            "latitude": 12.97,
            "longitude": 77.59,
            "rainfall": 5.0,
            "max_temp": 34.0,
            "min_temp": 20.0,
            "prediction_confidence": 0.65,
            "timestamp": "2024-01-04",
        },
    ]
    return mock


def test_forecast_viewer_render_does_not_crash(api):
    m = __import__("dashboard.page_views.02_forecast_viewer", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall", "horizon": 3})
    assert True


def test_forecast_viewer_no_current(api):
    api.get_current_state.return_value = None
    m = __import__("dashboard.page_views.02_forecast_viewer", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "Rainfall", "horizon": 3})
    assert True


def test_forecast_viewer_no_forecast(api):
    api.get_forecast.return_value = []
    m = __import__("dashboard.page_views.02_forecast_viewer", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "MaxTemp", "horizon": 1})
    assert True


def test_forecast_viewer_temp_variable(api):
    m = __import__("dashboard.page_views.02_forecast_viewer", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "variable": "MaxTemp", "horizon": 7})
    assert True
