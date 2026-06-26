"""Unit tests for scenario builder and presets."""

from __future__ import annotations

import pytest


class TestCreateScenario:
    """Test the create_scenario function."""

    def test_create_temperature_scenario(self):
        from simulator.scenarios.scenario_builder import create_scenario

        s = create_scenario(
            scenario_id="custom_temp",
            name="Custom Temp",
            description="Test",
            scenario_type="temperature",
            parameters={"temperature_delta": 2.0},
        )
        assert s.scenario_id == "custom_temp"
        assert s.scenario_type == "temperature"
        assert s.parameters["temperature_delta"] == 2.0

    def test_create_rainfall_scenario(self):
        from simulator.scenarios.scenario_builder import create_scenario

        s = create_scenario(
            scenario_id="custom_rain",
            name="Custom Rain",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": 30.0},
        )
        assert s.parameters["rainfall_change_pct"] == 30.0

    def test_create_with_auto_id(self):
        from simulator.scenarios.scenario_builder import create_scenario

        s = create_scenario(
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        assert s.scenario_id.startswith("scenario_")
        assert s.scenario_type == "temperature"

    def test_create_invalid_scenario_raises(self):
        from simulator.scenarios.scenario_builder import create_scenario

        with pytest.raises(ValueError, match="Invalid scenario"):
            create_scenario(
                scenario_type="temperature",
                parameters={"temperature_delta": 100.0},
            )

    def test_create_monsoon_scenario(self):
        from simulator.scenarios.scenario_builder import create_scenario

        s = create_scenario(
            scenario_id="monsoon_test",
            name="Monsoon Test",
            description="",
            scenario_type="monsoon",
            parameters={"delay_days": 15, "intensity_reduction_pct": 10.0},
        )
        assert s.parameters["delay_days"] == 15


class TestPresetScenarios:
    """Test preset scenario access."""

    def test_list_preset_scenarios(self):
        from simulator.scenarios.scenario_builder import list_preset_scenarios

        presets = list_preset_scenarios()
        assert len(presets) >= 10
        preset_ids = {p["scenario_id"] for p in presets}
        assert "temp_plus_1" in preset_ids
        assert "temp_plus_2" in preset_ids
        assert "rain_plus_40" in preset_ids
        assert "heatwave" in preset_ids
        assert "flood" in preset_ids
        assert "drought" in preset_ids

    def test_get_preset_scenario(self):
        from simulator.scenarios.scenario_builder import get_preset_scenario

        s = get_preset_scenario("temp_plus_2")
        assert s is not None
        assert s.scenario_id == "temp_plus_2"
        assert s.scenario_type == "temperature"
        assert s.parameters["temperature_delta"] == 2.0

    def test_get_nonexistent_preset(self):
        from simulator.scenarios.scenario_builder import get_preset_scenario

        s = get_preset_scenario("nonexistent")
        assert s is None

    def test_preset_has_all_fields(self):
        from simulator.scenarios.scenario_builder import get_preset_scenario

        s = get_preset_scenario("flood")
        assert s is not None
        assert s.name == "Flood Scenario"
        assert s.description != ""
        assert s.parameters["event_type"] == "flood"
