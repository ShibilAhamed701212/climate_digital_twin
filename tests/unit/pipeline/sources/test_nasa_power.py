"""Tests for NASA POWER API connector."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import requests

from pipeline.sources.nasa_power import (
    COLUMN_MAP,
    NASA_PARAM_MAP,
    NASA_POWER_URL,
    fetch_nasa_power_grid,
    fetch_point,
    generate_grid,
    parse_response,
)

# ── generate_grid ──────────────────────────────────────────────────


class TestGenerateGrid:
    def test_single_point(self):
        bounds = {"min_lat": 10.0, "max_lat": 10.0, "min_lon": 20.0, "max_lon": 20.0}
        points = generate_grid(1.0, bounds)
        assert len(points) == 1
        assert points[0] == {"latitude": 10.0, "longitude": 20.0}

    def test_2x2_grid(self):
        bounds = {"min_lat": 10.0, "max_lat": 11.0, "min_lon": 20.0, "max_lon": 21.0}
        points = generate_grid(1.0, bounds)
        assert len(points) == 4

    def test_resolution_rounding(self):
        bounds = {"min_lat": 10.0, "max_lat": 10.5, "min_lon": 20.0, "max_lon": 20.5}
        points = generate_grid(0.5, bounds)
        assert len(points) == 4
        for p in points:
            assert isinstance(p["latitude"], float)
            assert isinstance(p["longitude"], float)

    def test_negative_coordinates(self):
        bounds = {"min_lat": -10.0, "max_lat": -9.0, "min_lon": -20.0, "max_lon": -19.0}
        points = generate_grid(1.0, bounds)
        assert len(points) == 4
        assert points[0]["latitude"] == -10.0
        assert points[0]["longitude"] == -20.0


# ── fetch_point ────────────────────────────────────────────────────


class TestFetchPoint:
    def test_successful_fetch(self):
        mock_data = {"properties": {"parameter": {}}}
        source_config = {"parameters": NASA_PARAM_MAP}
        with patch("pipeline.sources.nasa_power.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.headers = {"Content-Type": "application/json"}
            mock_get.return_value.text = '{"properties": {"parameter": {}}}'
            mock_get.return_value.json.return_value = mock_data
            result = fetch_point(10.0, 20.0, "20200101", "20200131", source_config)
        assert result == mock_data
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["latitude"] == 10.0
        assert kwargs["params"]["longitude"] == 20.0

    def test_fetch_failure_returns_none(self):
        source_config = {"parameters": NASA_PARAM_MAP}
        with patch("pipeline.sources.nasa_power.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("connection error")
            result = fetch_point(10.0, 20.0, "20200101", "20200131", source_config)
        assert result is None

    def test_fetch_custom_config(self):
        source_config = {
            "parameters": {"precip": "PRECTOTCORR"},
            "community": "RC",
            "format": "CSV",
            "endpoint": "https://custom.example.com",
        }
        with patch("pipeline.sources.nasa_power.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}
            fetch_point(10.0, 20.0, "20200101", "20200131", source_config)
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["community"] == "RC"
        assert kwargs["params"]["format"] == "CSV"
        assert args[0] == "https://custom.example.com"

    def test_url_construction(self):
        source_config = {"parameters": NASA_PARAM_MAP}
        with patch("pipeline.sources.nasa_power.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}
            fetch_point(10.0, 20.0, "20200101", "20200131", source_config)
        args, _ = mock_get.call_args
        assert args[0] == NASA_POWER_URL


# ── parse_response ─────────────────────────────────────────────────


class TestParseResponse:
    def test_none_data_returns_none(self):
        assert parse_response(None, 10.0, 20.0, {"parameters": NASA_PARAM_MAP}) is None

    def test_empty_params_returns_none(self):
        data = {"properties": {"parameter": {}}}
        result = parse_response(data, 10.0, 20.0, {"parameters": NASA_PARAM_MAP})
        assert result is None

    def test_valid_response(self):
        data = {
            "properties": {
                "parameter": {
                    "PRECTOTCORR": {"20200101": "1.5", "20200102": "2.0"},
                    "T2M_MAX": {"20200101": "30.0", "20200102": "32.0"},
                    "T2M_MIN": {"20200101": "20.0", "20200102": "22.0"},
                }
            }
        }
        result = parse_response(data, 10.0, 20.0, {"parameters": NASA_PARAM_MAP})
        assert result is not None
        assert "rainfall" in result
        assert "max_temp" in result
        assert "min_temp" in result
        assert len(result["rainfall"]) == 2
        assert "Date" in result["rainfall"].columns
        assert "Rainfall" in result["rainfall"].columns
        assert result["rainfall"]["Rainfall"].iloc[0] == 1.5

    def test_custom_param_map(self):
        data = {
            "properties": {
                "parameter": {
                    "PRECTOTCORR": {"20200101": "1.5"},
                }
            }
        }
        result = parse_response(data, 10.0, 20.0, {"parameters": {"precip": "PRECTOTCORR"}})
        assert result is not None
        assert "precip" in result

    def test_missing_keys_handled(self):
        data = {"properties": {"parameter": {"PRECTOTCORR": {"20200101": "1.5"}}}}
        result = parse_response(data, 10.0, 20.0, {"parameters": NASA_PARAM_MAP})
        assert result is not None
        assert "max_temp" not in result

    def test_malformed_data_returns_none(self):
        data = {"not_properties": {}}
        result = parse_response(data, 10.0, 20.0, {"parameters": NASA_PARAM_MAP})
        assert result is None


# ── fetch_nasa_power_grid ──────────────────────────────────────────


class TestFetchNasaPowerGrid:
    def test_empty_grid(self):
        bounds = {"min_lat": 10.0, "max_lat": 10.0, "min_lon": 20.0, "max_lon": 20.0}
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 31)
        source_config = {"resolution": 1.0, "max_workers": 2, "parameters": NASA_PARAM_MAP}
        mock_point_data = {
            "properties": {
                "parameter": {
                    "PRECTOTCORR": {"20200101": "1.0"},
                    "T2M_MAX": {"20200101": "30.0"},
                    "T2M_MIN": {"20200101": "20.0"},
                }
            }
        }
        with patch("pipeline.sources.nasa_power.fetch_point", return_value=mock_point_data):
            result = fetch_nasa_power_grid(bounds, start, end, source_config)
        assert "rainfall" in result
        assert not result["rainfall"].empty

    def test_all_points_fail(self):
        bounds = {"min_lat": 10.0, "max_lat": 10.0, "min_lon": 20.0, "max_lon": 20.0}
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 31)
        source_config = {"resolution": 1.0, "max_workers": 2, "parameters": NASA_PARAM_MAP}
        with patch("pipeline.sources.nasa_power.fetch_point", return_value=None):
            result = fetch_nasa_power_grid(bounds, start, end, source_config)
        assert result == {}

    def test_partial_parse_failure(self):
        bounds = {"min_lat": 10.0, "max_lat": 11.0, "min_lon": 20.0, "max_lon": 21.0}
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 31)
        source_config = {"resolution": 1.0, "max_workers": 2, "parameters": NASA_PARAM_MAP}
        good_data = {
            "properties": {
                "parameter": {
                    "PRECTOTCORR": {"20200101": "1.0"},
                    "T2M_MAX": {"20200101": "30.0"},
                    "T2M_MIN": {"20200101": "20.0"},
                }
            }
        }
        call_count = 0
        side_effects = [good_data, good_data, None, None]

        def _mock_fetch(*args, **kwargs):
            nonlocal call_count
            val = side_effects[call_count % len(side_effects)]
            call_count += 1
            return val

        with patch("pipeline.sources.nasa_power.fetch_point", side_effect=_mock_fetch):
            result = fetch_nasa_power_grid(bounds, start, end, source_config)
        assert "rainfall" in result


# ── Constants / Interface ──────────────────────────────────────────────


class TestConstants:
    def test_nasa_param_map_keys(self):
        assert "rainfall" in NASA_PARAM_MAP
        assert "max_temp" in NASA_PARAM_MAP
        assert "min_temp" in NASA_PARAM_MAP

    def test_column_map(self):
        assert COLUMN_MAP["rainfall"] == "Rainfall"
        assert COLUMN_MAP["max_temp"] == "MaxTemp"
        assert COLUMN_MAP["min_temp"] == "MinTemp"
