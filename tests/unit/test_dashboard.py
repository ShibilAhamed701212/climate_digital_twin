"""Unit tests for the Phase 5 dashboard module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
        assert API_BASE_URL == "http://localhost:8001/api/v1"
        assert KARNATAKA_BOUNDS["min_lat"] == 11.5
        assert PAGE_CONFIG["layout"] == "wide"
        assert len(PAGES) == 7
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
        expected = {"status": "success", "data": {"location_id": "KA-BLR-001", "rainfall": 50.0}}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = api.get_current_state("KA-BLR-001")
        assert result["location_id"] == "KA-BLR-001"
        assert result["rainfall"] == 50.0

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_current_state_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        result = api.get_current_state("KA-BLR-001")
        assert result is not None
        assert result["location_id"] == "KA-BLR-001"
        assert "rainfall" in result
        assert "max_temp" in result
        assert "min_temp" in result

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_forecast_with_backend(self, mock_get, api):
        expected = {
            "status": "success",
            "data": [
                {"location_id": "KA-BLR-001", "rainfall": 50.0, "prediction_confidence": 0.9},
                {"location_id": "KA-BLR-001", "rainfall": 45.0, "prediction_confidence": 0.8},
            ],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = api.get_forecast("KA-BLR-001", horizon=2)
        assert len(result) == 2
        assert result[0]["rainfall"] == 50.0

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_forecast_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        result = api.get_forecast("KA-BLR-001", horizon=3)
        assert len(result) == 3
        assert all(f["state_type"] == "forecast" for f in result)

    def test_get_scenarios(self, api):
        scenarios = api.get_scenarios()
        assert len(scenarios) >= 5
        scenario_ids = [s["id"] for s in scenarios]
        assert "temp_plus_2" in scenario_ids
        assert "rain_plus_20" in scenario_ids

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_scenarios_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        scenarios = api.get_scenarios()
        assert len(scenarios) >= 5

    def test_simulate_scenario_synthetic(self, api):
        params = {
            "scenario_id": "temp_plus_2",
            "location_id": "KA-BLR-001",
            "temperature_delta": 2.0,
            "rainfall_change_pct": 10,
        }
        result = api.simulate_scenario(params)
        assert result is not None
        assert "data" in result
        assert result["data"]["scenario_id"] == "temp_plus_2"
        assert result["data"]["state_type"] == "scenario"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_risk_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        result = api.get_risk("KA-BLR-001")
        assert result is not None
        assert "composite_risk" in result
        assert "heat_risk" in result
        assert "shap_summary" in result

    def test_get_district_summary(self, api):
        summary = api.get_district_summary("Bengaluru Urban")
        assert summary is not None
        assert summary["district"] == "Bengaluru Urban"
        assert "total_rainfall_ytd" in summary
        assert "risk_level" in summary


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
