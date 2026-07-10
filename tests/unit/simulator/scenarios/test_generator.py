"""Unit tests for simulator/scenarios/generator.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from simulator.models.scenario_models import ScenarioDefinition


@pytest.fixture
def generator():
    from simulator.scenarios.generator import ScenarioGenerator

    return ScenarioGenerator()


class TestWarmingScenario:
    def test_basic_warming(self, generator):
        scenario = generator.warming_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            delta_c=2.0,
            duration_days=30,
        )
        assert scenario.scenario_type == "temperature"
        assert scenario.parameters["temperature_delta"] == 2.0
        assert scenario.parameters["warming_rate"] == 2.0 / 30
        assert scenario.parameters["location_id"] == "KA-BLR-001"

    def test_default_duration(self, generator):
        scenario = generator.warming_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            delta_c=1.5,
        )
        assert scenario.parameters["duration_days"] == 30

    def test_name_format(self, generator):
        scenario = generator.warming_scenario(
            location_id="L1", latitude=0.0, longitude=0.0, delta_c=3.0
        )
        assert "+3.0C Warming" in scenario.name


class TestRainfallScenario:
    def test_basic_rainfall(self, generator):
        scenario = generator.rainfall_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            multiplier=1.2,
            duration_days=30,
        )
        assert scenario.scenario_type == "rainfall"
        assert scenario.parameters["rainfall_multiplier"] == 1.2

    def test_negative_change(self, generator):
        scenario = generator.rainfall_scenario(
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            multiplier=0.8,
        )
        assert scenario.parameters["rainfall_change_pct"] == -20.0
        assert "-20%" in scenario.name

    def test_positive_change(self, generator):
        scenario = generator.rainfall_scenario(
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            multiplier=1.5,
        )
        assert scenario.parameters["rainfall_change_pct"] == 50.0
        assert "+50%" in scenario.name


class TestExtremeScenario:
    def test_extreme_values(self, generator):
        scenario = generator.extreme_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
        )
        assert scenario.scenario_type == "extreme_event"
        assert scenario.parameters["temperature_delta"] == 4.0
        assert scenario.parameters["rainfall_multiplier"] == 1.3
        assert scenario.parameters["humidity_delta"] == 5.0

    def test_custom_duration(self, generator):
        scenario = generator.extreme_scenario(
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            duration_days=7,
        )
        assert scenario.parameters["duration_days"] == 7
        assert scenario.parameters["warming_rate"] == 4.0 / 7


class TestDroughtScenario:
    def test_drought_values(self, generator):
        scenario = generator.drought_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
        )
        assert scenario.scenario_type == "extreme_event"
        assert scenario.parameters["temperature_delta"] == 2.0
        assert scenario.parameters["rainfall_multiplier"] == 0.8
        assert scenario.parameters["humidity_delta"] == -5.0
        assert scenario.parameters["drought_intensity"] == 0.6

    def test_default_duration(self, generator):
        scenario = generator.drought_scenario(location_id="L1", latitude=0.0, longitude=0.0)
        assert scenario.parameters["duration_days"] == 90


class TestIPCCScenario:
    def test_valid_pathway(self, generator):
        scenario = generator.ipcc_scenario(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            pathway="ssp585",
            year=2050,
        )
        assert scenario.scenario_type == "temperature"
        assert "IPCC SSP585" in scenario.name

    def test_invalid_pathway(self, generator):
        with pytest.raises(ValueError, match="Unknown pathway"):
            generator.ipcc_scenario(
                location_id="L1",
                latitude=0.0,
                longitude=0.0,
                pathway="invalid",
            )

    def test_case_insensitive(self, generator):
        scenario = generator.ipcc_scenario(
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            pathway="SSP126",
            year=2030,
        )
        assert scenario is not None
        assert "SSP126" in scenario.name

    def test_closest_year(self, generator):
        scenario = generator.ipcc_scenario(
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            pathway="ssp245",
            year=2040,
        )
        assert scenario.parameters["closest_year"] == 2030.0

    def test_duration_capped(self, generator):
        with patch("simulator.scenarios.generator.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, tzinfo=UTC)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            scenario = generator.ipcc_scenario(
                location_id="L1",
                latitude=0.0,
                longitude=0.0,
                pathway="ssp119",
                year=2100,
            )
            assert scenario.parameters["duration_days"] <= 365


class TestCustomScenario:
    def test_basic_custom(self, generator):
        scenario = generator.custom_scenario(
            name="Custom Test",
            description="A custom scenario",
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            parameters={"temperature_delta": 3.0},
        )
        assert scenario.name == "Custom Test"
        assert scenario.parameters["temperature_delta"] == 3.0

    def test_infer_temperature_type(self, generator):
        scenario = generator.custom_scenario(
            name="T",
            description="",
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            parameters={"temperature_delta": 2.0},
        )
        assert scenario.scenario_type == "temperature"

    def test_infer_combined_type(self, generator):
        scenario = generator.custom_scenario(
            name="C",
            description="",
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            parameters={"temperature_delta": 2.0, "rainfall_multiplier": 1.1},
        )
        assert scenario.scenario_type == "combined"

    def test_non_standard_keys_skipped(self, generator):
        scenario = generator.custom_scenario(
            name="Test",
            description="",
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            parameters={"temperature_delta": 2.0, "custom_list": [1, 2, 3]},
        )
        assert "custom_list" not in scenario.parameters

    def test_non_standard_string_included(self, generator):
        scenario = generator.custom_scenario(
            name="Test",
            description="",
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            parameters={"temperature_delta": 2.0, "notes": "important"},
        )
        assert scenario.parameters["notes"] == "important"


class TestValidateScenario:
    def test_valid_scenario(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={
                "latitude": 12.0,
                "longitude": 77.0,
                "duration_days": 30,
                "temperature_delta": 2.0,
            },
        )
        assert generator.validate_scenario(sc) == []

    def test_invalid_latitude(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"latitude": 100.0, "longitude": 0.0, "temperature_delta": 2.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Latitude" in i for i in issues)

    def test_invalid_longitude(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"latitude": 0.0, "longitude": 200.0, "temperature_delta": 2.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Longitude" in i for i in issues)

    def test_negative_duration(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"duration_days": -1, "temperature_delta": 2.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Duration" in i for i in issues)

    def test_excessive_duration(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"duration_days": 5000, "temperature_delta": 2.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("exceeds 10-year" in i for i in issues)

    def test_unrealistic_temperature_delta(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 50.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("unrealistic" in i for i in issues)

    def test_negative_rainfall_multiplier(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_multiplier": -1.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("must be positive" in i for i in issues)

    def test_excessive_rainfall_multiplier(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_multiplier": 10.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("> 5x" in i for i in issues)

    def test_unrealistic_humidity_delta(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="custom",
            parameters={"humidity_delta": 200.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Humidity delta" in i for i in issues)

    def test_unrealistic_wind_speed_delta(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="custom",
            parameters={"wind_speed_delta": 100.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Wind speed" in i for i in issues)

    def test_unrealistic_pressure_delta(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="custom",
            parameters={"pressure_delta": 100.0},
        )
        issues = generator.validate_scenario(sc)
        assert any("Pressure delta" in i for i in issues)

    def test_temperature_scenario_missing_delta(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={},
        )
        issues = generator.validate_scenario(sc)
        assert any("temperature_delta" in i for i in issues)

    def test_rainfall_scenario_missing_multiplier(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="rainfall",
            parameters={},
        )
        issues = generator.validate_scenario(sc)
        assert any("rainfall_multiplier" in i for i in issues)

    def test_duration_none_skips_validation(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"duration_days": None, "temperature_delta": 2.0},
        )
        issues = generator.validate_scenario(sc)
        assert not any("Duration" in i for i in issues)


class TestListPathways:
    def test_list_pathways(self, generator):
        pathways = generator.list_pathways()
        assert "ssp119" in pathways
        assert "ssp585" in pathways
        assert pathways == sorted(pathways)


class TestGetWarmingLevel:
    def test_valid_pathway(self, generator):
        level = generator.get_warming_level("ssp245", 2050)
        assert level == 1.8

    def test_invalid_pathway(self, generator):
        level = generator.get_warming_level("invalid", 2050)
        assert level is None

    def test_closest_year(self, generator):
        level = generator.get_warming_level("ssp119", 2040)
        assert level == 1.0

    def test_case_insensitive(self, generator):
        level = generator.get_warming_level("SSP370", 2100)
        assert level == 3.6


class TestInferScenarioType:
    def test_combined(self, generator):
        result = generator._infer_scenario_type(
            {"temperature_delta": 2.0, "rainfall_multiplier": 1.1}
        )
        assert result == "combined"

    def test_temperature_only(self, generator):
        result = generator._infer_scenario_type({"temperature_delta": 2.0})
        assert result == "temperature"

    def test_rainfall_only(self, generator):
        result = generator._infer_scenario_type({"rainfall_multiplier": 1.2})
        assert result == "rainfall"

    def test_other_params(self, generator):
        result = generator._infer_scenario_type({"humidity_delta": 5.0})
        assert result == "custom"

    def test_empty(self, generator):
        result = generator._infer_scenario_type({})
        assert result == "custom"


class TestEstimateEndDate:
    def test_with_duration(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"duration_days": 10},
        )
        end = generator.estimate_end_date(sc)
        assert end > datetime.now(UTC)

    def test_default_duration(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={},
        )
        end = generator.estimate_end_date(sc)
        assert end > datetime.now(UTC)

    def test_non_numeric_duration(self, generator):
        sc = ScenarioDefinition(
            scenario_id="s1",
            name="test",
            description="",
            scenario_type="temperature",
            parameters={"duration_days": "invalid"},
        )
        end = generator.estimate_end_date(sc)
        assert end > datetime.now(UTC)


class TestGetDefaultDuration:
    def test_known_type(self, generator):
        assert generator.get_default_duration("temperature") == 30
        assert generator.get_default_duration("extreme_event") == 14
        assert generator.get_default_duration("monsoon_shift") == 90

    def test_unknown_type(self, generator):
        assert generator.get_default_duration("unknown") == 30


class TestGenerateId:
    def test_id_format(self):
        from simulator.scenarios.generator import _generate_id

        id_val = _generate_id()
        assert id_val.startswith("scenario_")
        assert len(id_val) == 17  # "scenario_" + 8 hex chars


class TestCustomScenarioEdgeCases:
    def test_no_standard_params(self, generator):
        scenario = generator.custom_scenario(
            name="Edge",
            description="",
            location_id="L1",
            latitude=0.0,
            longitude=0.0,
            parameters={},
        )
        assert scenario.scenario_type == "custom"
        assert "latitude" in scenario.parameters
        assert "longitude" in scenario.parameters
