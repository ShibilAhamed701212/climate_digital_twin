"""Tests for merged Twin State shim (former 10_twin_state_bhai)."""

from __future__ import annotations

from importlib import import_module



class _StubApi:
    def get_current_state(self, entity_id):
        return {
            "location_id": entity_id,
            "current_temp": 22.1,
            "max_temp": 28.0,
            "min_temp": 20.0,
            "rainfall": 1.2,
            "humidity_pct": 88.0,
            "pressure_hpa": 907.5,
            "wind_speed_10m": 3.0,
            "data_source": "open_meteo",
            "quality_flag": "validated",
            "timestamp": "2026-07-30T00:00:00",
        }

    def get_all_locations(self):
        return [{"id": "KA-BLR-001", "lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"}]

    def get_historical(self, entity_id):
        return [
            {
                "timestamp": "2026-07-29T00:00:00",
                "rainfall": 0.5,
                "max_temp": 27.0,
                "min_temp": 19.0,
                "state_type": "historical",
            }
        ]

    def get_forecast(self, entity_id, horizon=3):
        return [
            {"rainfall": 1.0, "max_temp": 28.0, "min_temp": 20.0, "prediction_confidence": 0.8}
            for _ in range(horizon)
        ]

    def get_version_history(self, entity_id):
        return [
            {
                "version_number": 1,
                "created_at": "2026-07-29T00:00:00",
                "entity_id": entity_id,
                "state": {"rainfall": 0.5, "temperature_2m": 27.0, "data_source": "open_meteo"},
            }
        ]

    def compare_versions(self, entity_id, a, b):
        return [
            {"Variable": "rainfall", "Version A": 0.5, "Version B": 1.2, "Delta": 0.7},
        ]


def test_twin_state_bhai_shim_delegates_to_unified_page():
    m = import_module("dashboard.page_views.10_twin_state_bhai")
    m.render(_StubApi(), {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True


def test_unified_twin_state_page_renders():
    m = import_module("dashboard.page_views.03_twin_state")
    m.render(_StubApi(), {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True
