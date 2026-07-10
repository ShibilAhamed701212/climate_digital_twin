"""Tests for dashboard/pages/06_reports.py — render() function."""

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
    mock.get_district_summary.return_value = {
        "district": "Bengaluru Urban",
        "total_rainfall_ytd": 120.5,
        "avg_max_temp": 32.0,
        "avg_min_temp": 22.0,
        "rainy_days": 60,
        "extreme_heat_days": 10,
        "risk_level": "Moderate",
    }
    mock.get_historical.return_value = [
        {"timestamp": "2024-01-01", "rainfall": 10, "max_temp": 30, "min_temp": 22},
        {"timestamp": "2024-01-02", "rainfall": 15, "max_temp": 32, "min_temp": 21},
    ]
    mock.get_forecast.return_value = [
        {"rainfall": 10.0, "max_temp": 30.0, "min_temp": 22.0, "prediction_confidence": 0.85},
        {"rainfall": 8.0, "max_temp": 32.0, "min_temp": 21.0, "prediction_confidence": 0.75},
    ]
    return mock


def test_reports_render_does_not_crash(api):
    m = __import__("dashboard.page_views.06_reports", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "district": "All"})
    assert True


def test_reports_single_district(api):
    m = __import__("dashboard.page_views.06_reports", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "district": "Bengaluru Urban"})
    assert True


def test_reports_no_historical(api):
    api.get_historical.return_value = []
    m = __import__("dashboard.page_views.06_reports", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "district": "All"})
    assert True


def test_reports_no_forecast(api):
    api.get_forecast.return_value = []
    m = __import__("dashboard.page_views.06_reports", fromlist=["render"])

    m.render(api, {"location_id": "KA-BLR-001", "district": "All"})
    assert True
