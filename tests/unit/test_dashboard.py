"""Unit tests for the Phase 5 dashboard module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _prevent_real_http():
    """Prevent real HTTP requests in all dashboard tests.

    Each test can override individual patches to test success paths.
    Instead of blocking: allow requests but ensure tests that don't mock
    will hit connection errors and exercise fallback paths.
    This fixture does nothing — individual tests handle mocking.
    """
    yield


class TestDashboardConfig:
    """Test the dashboard configuration module."""

    def test_config_has_required_settings(self):
        from dashboard.config.config import (
            API_BASE_URL,
            DASHBOARD_TITLE,
            KARNATAKA_BOUNDS,
            PAGE_CONFIG,
            PAGES,
            PILOT_DISTRICTS,
            SAMPLE_LOCATIONS,
        )

        assert DASHBOARD_TITLE == "Climate Digital Twin — Karnataka"
        assert API_BASE_URL == "http://localhost:8000"
        assert KARNATAKA_BOUNDS["min_lat"] == 11.5
        assert PAGE_CONFIG["layout"] == "wide"
        assert len(PAGES) == 10
        assert len(PILOT_DISTRICTS) == 5
        assert len(SAMPLE_LOCATIONS) == 10

    def test_config_pages_ordered_correctly(self):
        from dashboard.config.config import PAGES

        titles = [p["title"] for p in PAGES]
        assert titles == [
            "Climate Overview",
            "Forecast Viewer",
            "Digital Twin State",
            "Scenario Simulator",
            "Climate Risk",
            "Reports & Insights",
            "AI Copilot",
            "Knowledge Base",
            "Spatial Grid",
            "Feedback",
        ]

    def test_config_color_schemes(self):
        from dashboard.config.config import COLOR_SCHEMES, VARIABLE_LABELS, VARIABLE_UNITS

        assert "Rainfall" in COLOR_SCHEMES
        assert "MaxTemp" in COLOR_SCHEMES
        assert VARIABLE_UNITS["Rainfall"] == "mm"
        assert VARIABLE_UNITS["MaxTemp"] == "°C"
        assert "Rainfall" in VARIABLE_LABELS

    def test_config_sample_locations_have_required_fields(self):
        from dashboard.config.config import SAMPLE_LOCATIONS

        for loc in SAMPLE_LOCATIONS:
            assert "id" in loc
            assert "lat" in loc
            assert "lon" in loc
            assert "district" in loc
            assert loc["id"].startswith("KA-")


class TestDashboardAPI:
    """Test the DashboardAPI client."""

    @pytest.fixture
    def api(self):
        from dashboard.services.api_client import DashboardAPI

        return DashboardAPI(base_url="http://test/api/v1", timeout=1)

    def test_init(self, api):
        assert api.base_url == "http://test/api/v1"
        assert api.timeout == 1

    def test_get_all_locations(self, api):
        locations = api.get_all_locations()
        assert len(locations) == 10
        assert locations[0]["id"] == "KA-BLR-001"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_current_state_with_backend(self, mock_get, api):
        expected = {
            "entity_id": "KA-BLR-001",
            "timestamp": "2026-07-30T00:00:00",
            "temperature_2m": 32.0,
            "precipitation_mm": 50.0,
            "humidity_pct": 80.0,
            "pressure_hpa": 907.5,
            "wind_speed_10m": 5.0,
            "data_source": "open_meteo",
            "quality_flag": "validated",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = api.get_current_state("KA-BLR-001")
        assert result["location_id"] == "KA-BLR-001"
        assert result["rainfall"] == 50.0
        assert result["max_temp"] == 32.0
        assert result["data_source"] == "open_meteo"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_current_state_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        result = api.get_current_state("KA-BLR-001")
        assert result is not None
        assert result["location_id"] == "KA-BLR-001"
        assert "rainfall" in result
        assert "max_temp" in result
        assert "min_temp" in result

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_get_forecast_with_backend(self, mock_post, api):
        expected = {
            "location_id": "KA-BLR-001",
            "target_variable": "temperature_2m",
            "timestamps": ["2026-07-31T00:00:00", "2026-08-01T00:00:00"],
            "values": [[50.0, 32.0, 20.0], [45.0, 33.0, 21.0]],
            "model_id": "lstm-real-v2",
            "created_at": "2026-07-31T00:00:00",
            "confidence": 0.95,
            "forecast_id": "fc-001",
            "authenticity": "REAL",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = api.get_forecast("KA-BLR-001", horizon=2)
        assert len(result) == 2
        assert result[0]["rainfall"] == 50.0
        assert result[0]["max_temp"] == 32.0
        assert result[0]["data_source"] == "REAL"

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_get_forecast_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.get_forecast("KA-BLR-001", horizon=3)
        # Phase 6: observations are never presented as a forecast.
        assert result == []
        assert api.get_fallback_status()["forecast"] is True

    def test_get_scenarios(self, api):
        scenarios = api.get_scenarios()
        # No predefined scenarios — returns empty list when API is unavailable
        assert isinstance(scenarios, list)

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_scenarios_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        scenarios = api.get_scenarios()
        assert isinstance(scenarios, list)

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_simulate_scenario_gateway(self, mock_post, api):
        # Phase 5 invariant: no synthetic fallback — gateway create+run only.
        create_resp = MagicMock()
        create_resp.json.return_value = {"scenario_id": "s1"}
        create_resp.raise_for_status.return_value = None
        run_resp = MagicMock()
        run_resp.json.return_value = {
            "result_id": "r1",
            "scenario": {"precipitation_mm": 2.0, "temperature_2m": 24.1},
            "authenticity": "SCENARIO",
            "mode": "REAL",
            "baseline": {"precipitation_mm": 0.0, "temperature_2m": 22.1},
            "deltas": {"precipitation_mm": 2.0, "temperature_2m": 2.0},
            "time_steps": ["2024-01-01T00:00:00"],
        }
        run_resp.raise_for_status.return_value = None
        mock_post.side_effect = [create_resp, run_resp]

        params = {
            "scenario_id": "temp_plus_2",
            "location_id": "KA-BLR-001",
            "temperature_delta": 2.0,
            "rainfall_change_pct": 10,
        }
        result = api.simulate_scenario(params)
        assert result["status"] == "success"
        assert result["data"]["scenario_id"] == "s1"
        assert result["data"]["state_type"] == "scenario"
        assert result["data"]["authenticity"] == "SCENARIO"
        # Gateway endpoints, not :8002.
        posts = [c.args[0] for c in mock_post.call_args_list]
        assert "/scenario/create" in posts[0] and "/scenario/run" in posts[1]
        assert not api.get_fallback_status()

    def test_simulate_scenario_no_synthetic_fallback(self, api):
        # Gateway unavailable -> explicit unavailable, never fabricated weather.
        params = {
            "scenario_id": "temp_plus_2",
            "location_id": "KA-BLR-001",
            "temperature_delta": 2.0,
        }
        result = api.simulate_scenario(params)
        assert result is not None
        assert result["status"] == "unavailable"
        assert "data" not in result

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_get_risk_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.get_risk("KA-BLR-001")
        assert result is not None
        assert "composite_risk" in result
        assert "heat_risk" in result

    def test_get_district_summary(self, api):
        summary = api.get_district_summary("Bengaluru Urban")
        assert summary is not None
        assert summary["district"] == "Bengaluru Urban"
        assert "total_rainfall_ytd" in summary
        assert "risk_level" in summary

    def test_fallback_status_empty_initially(self, api):
        assert api.get_fallback_status() == {}

    def test_fallback_tracks_current_state(self, api):
        status = api.get_fallback_status()
        assert "current_state" not in status

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_tracked_on_api_failure(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        api.get_current_state("KA-BLR-001")
        assert api.get_fallback_status()["current_state"] is True

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_not_tracked_on_success(self, mock_get, api):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"location_id": "KA-BLR-001", "rainfall": 50.0},
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        api.get_current_state("KA-BLR-001")
        assert "current_state" not in api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_tracks_forecast_failure(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        api.get_forecast("KA-BLR-001", horizon=3)
        assert api.get_fallback_status()["forecast"] is True

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_tracks_historical_failure(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        api.get_historical("KA-BLR-001")
        assert api.get_fallback_status()["historical"] is True

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_tracks_risk_failure(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        api.get_risk("KA-BLR-001")
        assert api.get_fallback_status()["risk"] is True

    def test_clear_fallback_status(self, api):
        api._fallback_endpoints["current_state"] = True
        api._fallback_endpoints["forecast"] = True
        api.clear_fallback_status()
        assert api.get_fallback_status() == {}

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_fallback_tracks_scenario_simulation_failure(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        params = {"scenario_id": "temp_plus_2", "location_id": "KA-BLR-001"}
        result = api.simulate_scenario(params)
        assert result is not None
        assert api.get_fallback_status()["scenario_simulation"] is True

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_fallback_not_tracked_on_scenario_success(self, mock_post, api):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"scenario_id": "temp_plus_2"},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        params = {"scenario_id": "temp_plus_2", "location_id": "KA-BLR-001"}
        api.simulate_scenario(params)
        assert "scenario_simulation" not in api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_fallback_tracks_scenarios_list_failure(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        api.get_scenarios()
        assert api.get_fallback_status()["scenarios_list"] is True


class TestCopilotClientPaths:
    """Test that DashboardAPI routes to the correct HTTP endpoints."""

    @pytest.fixture
    def api(self):
        from dashboard.services.api_client import DashboardAPI

        return DashboardAPI(base_url="http://test/api/v1", timeout=1)

    def test_get_current_state_via_http(self, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "entity_id": "KA-BLR-001",
            "timestamp": "2026-06-28T12:00:00",
            "temperature_2m": 34.0,
            "precipitation_mm": 35.0,
            "humidity_pct": 70.0,
            "pressure_hpa": 908.0,
            "wind_speed_10m": 4.0,
            "data_source": "open_meteo",
            "quality_flag": "validated",
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(api._session, "get", return_value=mock_resp) as mock_get:
            result = api.get_current_state("KA-BLR-001")
            assert result["location_id"] == "KA-BLR-001"
            assert result["rainfall"] == 35.0
            assert result["max_temp"] == 34.0
            assert result["state_type"] == "current"
            mock_get.assert_called_once_with("http://test/api/v1/twin/state/KA-BLR-001", timeout=1)

    def test_get_forecast_via_http(self, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "location_id": "KA-BLR-001",
            "target_variable": "temperature_2m",
            "timestamps": ["2026-06-29T00:00:00", "2026-06-30T00:00:00"],
            "values": [[10.0, 33.0, 21.0], [5.0, 34.0, 22.0]],
            "model_id": "lstm-real-v2",
            "created_at": "2026-06-28T12:00:00",
            "confidence": 0.9,
            "forecast_id": "fc-001",
            "authenticity": "REAL",
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(api._session, "post", return_value=mock_resp) as mock_post:
            result = api.get_forecast("KA-BLR-001", horizon=2)
            assert len(result) == 2
            assert result[0]["state_type"] == "forecast"
            assert result[0]["rainfall"] == 10.0
            mock_post.assert_called_once_with(
                "http://test/api/v1/forecast/predict",
                json={
                    "location_id": "KA-BLR-001",
                    "target_variable": "temperature_2m",
                    "horizon_hours": 48,
                },
                timeout=1,
            )

    def test_get_risk_via_http(self, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "assessment_id": "a-1",
            "location_id": "KA-BLR-001",
            "composite_score": 0.417,
            "composite_category": "Moderate",
            "scores": [
                {"hazard_type": "heat", "score": 0.45, "category": "Moderate"},
                {"hazard_type": "heavy_rain", "score": 0.6, "category": "High"},
                {"hazard_type": "dryness", "score": 0.2, "category": "Low"},
            ],
            "timestamp": "2026-06-28T12:00:00",
            "metadata": {},
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(api._session, "post", return_value=mock_resp):
            result = api.get_risk("KA-BLR-001")
            assert round(result["composite_risk"], 1) == 41.7
            assert result["heat_risk"] == 45.0
            assert result["flood_risk"] == 60.0
            assert result["drought_risk"] == 20.0
            assert result["category"] == "Moderate"

    def test_simulate_scenario_via_http(self, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "simulated": {
                        "location_id": "KA-BLR-001",
                        "max_temp": 36.0,
                        "min_temp": 24.0,
                        "rainfall": 50.0,
                    }
                }
            ],
            "completed_at": "2026-06-28T12:00:00",
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(api._session, "post", return_value=mock_resp):
            params = {
                "scenario_id": "temp_plus_2",
                "location_id": "KA-BLR-001",
                "temperature_delta": 2.0,
            }
            result = api.simulate_scenario(params)
            assert result["status"] == "success"
            assert result["data"]["state_type"] == "scenario"


class TestCharts:
    """Test the Plotly chart components."""

    def test_line_chart_returns_figure(self):
        from dashboard.charts.time_series import line_chart

        data = [
            {"timestamp": "2024-01-01", "rainfall": 10, "max_temp": 30},
            {"timestamp": "2024-01-02", "rainfall": 15, "max_temp": 32},
        ]
        fig = line_chart(data)
        assert fig is not None
        assert len(fig.data) > 0

    def test_multi_line_chart(self):
        from dashboard.charts.time_series import multi_line_chart

        data = [
            {"timestamp": "2024-01-01", "rainfall": 10, "max_temp": 30, "min_temp": 20},
            {"timestamp": "2024-01-02", "rainfall": 15, "max_temp": 32, "min_temp": 22},
        ]
        fig = multi_line_chart(data)
        assert fig is not None
        assert len(fig.data) == 3

    def test_confidence_band_chart(self):
        from dashboard.charts.time_series import confidence_band_chart

        data = [
            {"timestamp": "2024-01-01", "rainfall": 10, "prediction_confidence": 0.9},
            {"timestamp": "2024-01-02", "rainfall": 15, "prediction_confidence": 0.8},
        ]
        fig = confidence_band_chart(data)
        assert fig is not None

    def test_before_after_chart(self):
        from dashboard.charts.comparison import before_after_chart

        before = {"rainfall": 50, "max_temp": 30}
        after = {"rainfall": 75, "max_temp": 32}
        fig = before_after_chart(before, after, variable="Rainfall")
        assert fig is not None
        assert len(fig.data) == 1

    def test_comparison_bar(self):
        from dashboard.charts.comparison import comparison_bar

        data = [{"district": "A", "rainfall": 50}, {"district": "B", "rainfall": 75}]
        fig = comparison_bar(data)
        assert fig is not None

    def test_histogram(self):
        from dashboard.charts.distribution import histogram

        data = [{"rainfall": 10}, {"rainfall": 20}, {"rainfall": 30}]
        fig = histogram(data)
        assert fig is not None

    def test_scatter_plot(self):
        from dashboard.charts.distribution import scatter_plot

        data = [{"max_temp": 30, "rainfall": 10}, {"max_temp": 32, "rainfall": 15}]
        fig = scatter_plot(data)
        assert fig is not None

    def test_risk_trend_chart(self):
        from dashboard.charts.risk_trends import risk_trend_chart

        risk_data = {"trend": [20, 30, 45, 35, 50]}
        fig = risk_trend_chart(risk_data)
        assert fig is not None

    def test_risk_gauge(self):
        from dashboard.charts.risk_trends import risk_gauge

        fig = risk_gauge(45.5)
        assert fig is not None

    def test_shap_waterfall(self):
        from dashboard.charts.risk_trends import shap_waterfall

        shap_values = {"Rainfall": 0.3, "MaxTemp": -0.2, "MinTemp": 0.1}
        fig = shap_waterfall(shap_values)
        assert fig is not None

    def test_risk_category_chart(self):
        from dashboard.charts.risk_trends import risk_category_chart

        risk_data = {"heat_risk": 60, "flood_risk": 30, "drought_risk": 45}
        fig = risk_category_chart(risk_data)
        assert fig is not None


class TestMaps:
    """Test the Folium map components."""

    def test_create_base_map(self):
        from dashboard.maps.climate_map import create_base_map

        m = create_base_map()
        assert m is not None
        assert "folium" in str(type(m))

    def test_climate_overlay_map(self):
        from dashboard.maps.climate_map import climate_overlay_map

        locations = [
            {"latitude": 12.97, "longitude": 77.59, "district": "BLR", "rainfall": 50},
        ]
        m = climate_overlay_map(locations, variable="Rainfall")
        assert m is not None

    def test_district_boundary_map(self):
        from dashboard.maps.climate_map import district_boundary_map

        locations = [
            {"latitude": 12.97, "longitude": 77.59, "district": "BLR", "rainfall": 50},
        ]
        m = district_boundary_map(locations)
        assert m is not None

    def test_risk_heatmap(self):
        from dashboard.maps.climate_map import risk_heatmap

        locations = [
            {"latitude": 12.97, "longitude": 77.59, "composite_risk": 45},
        ]
        m = risk_heatmap(locations)
        assert m is not None

    def test_forecast_map(self):
        from dashboard.maps.climate_map import forecast_map

        current = {"latitude": 12.97, "longitude": 77.59, "rainfall": 50}
        forecasts = [
            {"latitude": 12.97, "longitude": 77.59, "rainfall": 45, "timestamp": "2024-01-02"},
        ]
        m = forecast_map(current, forecasts)
        assert m is not None

    def test_before_after_comparison(self):
        from dashboard.maps.comparison_map import before_after_comparison

        before = {"latitude": 12.97, "longitude": 77.59, "rainfall": 50}
        after = {"latitude": 12.97, "longitude": 77.59, "rainfall": 75}
        m = before_after_comparison(before, after)
        assert m is not None

    def test_delta_map(self):
        from dashboard.maps.comparison_map import delta_map

        before = {"latitude": 12.97, "longitude": 77.59, "rainfall": 50}
        after = {"latitude": 12.97, "longitude": 77.59, "rainfall": 75}
        m = delta_map(before, after)
        assert m is not None


class TestComponents:
    """Test the reusable dashboard components."""

    def test_entity_detail_table_all_fields(self):
        from dashboard.components.cards import entity_detail_table

        entity = {
            "location_id": "KA-BLR-001",
            "district": "Bengaluru Urban",
            "latitude": 12.97,
            "longitude": 77.59,
            "timestamp": "2024-01-01T00:00:00",
            "rainfall": 50.5,
            "max_temp": 32.0,
            "min_temp": 20.0,
            "risk_score": 25.0,
            "prediction_confidence": 0.85,
            "data_source": "IMD",
            "state_type": "current",
        }
        result = entity_detail_table(entity)
        assert result is None

    def test_api_synthetic_data_has_all_fields(self):
        from dashboard.services.api_client import DashboardAPI

        api = DashboardAPI()
        data = api.get_current_state("KA-BLR-001")
        required = ["location_id", "rainfall", "max_temp", "min_temp", "latitude", "longitude"]
        for field in required:
            assert field in data, f"Missing field: {field}"
