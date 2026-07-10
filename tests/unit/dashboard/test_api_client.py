"""Tests for dashboard.services.api_client — covering remaining uncovered lines."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def api():
    from dashboard.services.api_client import DashboardAPI

    return DashboardAPI(base_url="http://test/api/v1", timeout=1)


class TestApiClientHistorical:
    """Cover get_historical — success path (lines 266-271)."""

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_historical_success(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "location_id": "KA-BLR-001",
                "timestamp": "2024-01-01",
                "rainfall": 10,
                "max_temp": 30,
                "min_temp": 20,
            },
            {
                "location_id": "KA-BLR-001",
                "timestamp": "2024-01-02",
                "rainfall": 15,
                "max_temp": 32,
                "min_temp": 22,
            },
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = api.get_historical("KA-BLR-001")
        assert len(result) == 2
        assert result[0]["state_type"] == "historical"
        assert result[0]["rainfall"] == 10

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_historical_empty_response(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = api.get_historical("KA-BLR-001")
        assert result == []

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_historical_fallback(self, mock_get, api):
        mock_get.side_effect = ConnectionError("API unavailable")
        result = api.get_historical("KA-BLR-001")
        assert result == []
        assert api.get_fallback_status()["historical"] is True

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_historical_truncates_to_90(self, mock_get, api):
        many = [{"timestamp": f"2024-01-{d:02d}", "rainfall": d} for d in range(1, 200)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = many
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = api.get_historical("KA-BLR-001")
        assert len(result) == 90


class TestApiClientScenariosSuccess:
    """Cover get_scenarios success path (lines 294-297)."""

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_scenarios_success_list(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "custom_1", "name": "Custom"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = api.get_scenarios()
        assert len(result) == 1
        assert result[0]["id"] == "custom_1"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_scenarios_success_non_list(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"not": "a list"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = api.get_scenarios()
        assert len(result) > 5
        assert not api.get_fallback_status()


class TestApiClientMonteCarlo:
    """Cover run_monte_carlo (lines 347-364)."""

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_run_monte_carlo_success(self, mock_post, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "completed", "results": []}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = api.run_monte_carlo("temperature", {"base": 1}, 500, 0.90)
        assert result["status"] == "completed"
        assert not api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_run_monte_carlo_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.run_monte_carlo()
        assert result is None
        assert api.get_fallback_status()["monte_carlo"] is True


class TestApiClientCompareScenarios:
    """Cover compare_scenarios (lines 374-386)."""

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_compare_scenarios_success(self, mock_post, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"comparison": "results"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        scenarios = [{"id": "a"}, {"id": "b"}]
        result = api.compare_scenarios(scenarios, 0)
        assert result == {"comparison": "results"}
        assert not api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_compare_scenarios_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.compare_scenarios([{"id": "a"}])
        assert result is None
        assert api.get_fallback_status()["compare_scenarios"] is True


class TestApiClientRunEnsemble:
    """Cover run_ensemble (lines 396-408)."""

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_run_ensemble_success(self, mock_post, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ensemble": "result"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = api.run_ensemble([{"params": {}}], "KA-BLR-001")
        assert result == {"ensemble": "result"}
        assert not api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_run_ensemble_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.run_ensemble([{"params": {}}])
        assert result is None
        assert api.get_fallback_status()["ensemble"] is True


class TestApiClientGenerateScenario:
    """Cover generate_scenario (lines 422-441)."""

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_generate_scenario_success(self, mock_post, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"generated": "scenario"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = api.generate_scenario(
            "heatwave", "KA-BLR-001", 12.97, 77.59, 30, {"intensity": 0.8}
        )
        assert result == {"generated": "scenario"}
        assert not api.get_fallback_status()

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_generate_scenario_fallback(self, mock_post, api):
        mock_post.side_effect = ConnectionError("API unavailable")
        result = api.generate_scenario("heatwave", "KA-BLR-001", 12.97, 77.59)
        assert result is None
        assert api.get_fallback_status()["generate_scenario"] is True


class TestApiClientDistrictSummary:
    """Cover get_district_summary branches (lines 494, 508, 511-514, 524)."""

    def test_get_district_summary_unknown_district(self, api):
        result = api.get_district_summary("Nonexistent District")
        assert result["error"] == "District not found"
        assert result["rainy_days"] == 0

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_district_summary_low_risk(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"composite_risk": 10, "category": "Low"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = api.get_district_summary("Bengaluru Urban")
        assert result["risk_level"] == "Low"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_district_summary_moderate_risk(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"composite_risk": 30, "category": "Moderate"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = api.get_district_summary("Bengaluru Urban")
        assert result["risk_level"] == "Moderate"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_district_summary_high_risk(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"composite_risk": 60, "category": "High"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = api.get_district_summary("Bengaluru Urban")
        assert result["risk_level"] == "High"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_district_summary_severe_risk(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"composite_risk": 80, "category": "Severe"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = api.get_district_summary("Bengaluru Urban")
        assert result["risk_level"] == "Severe"

    def test_get_district_summary_no_state(self, api):
        with patch.object(api, "get_current_state", return_value=None):
            result = api.get_district_summary("Bengaluru Urban")
            assert result["error"] == "No data available"

    @patch("dashboard.services.api_client.requests.Session.get")
    def test_get_district_summary_no_risk(self, mock_get, api):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = [
            {"location_id": "KA-BLR-001", "rainfall": 50, "max_temp": 32, "min_temp": 20},
            ValueError("no risk"),
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = api.get_district_summary("Bengaluru Urban")
        assert result["risk_level"] == "Moderate"


class TestApiClientCreateClient:
    """Cover create_api_client (line 533)."""

    def test_create_api_client(self):
        from dashboard.services.api_client import DashboardAPI, create_api_client

        client = create_api_client()
        assert isinstance(client, DashboardAPI)
        assert client.base_url == "http://twin-state-mgr:8001/api/v1"


class TestApiClientSimulateScenarioSuccessWithNoResults:
    """Cover simulate_scenario when results_list is empty."""

    @patch("dashboard.services.api_client.requests.Session.post")
    def test_simulate_scenario_no_results(self, mock_post, api):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [], "completed_at": "2024-01-01T00:00:00"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = api.simulate_scenario({"scenario_id": "temp_plus_2", "location_id": "KA-BLR-001"})
        assert result["status"] == "success"
        assert result["data"] == {}
