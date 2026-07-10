"""Unit tests for simulator/validators/scenario_validator.py."""

from __future__ import annotations

import pytest

from simulator.validators.scenario_validator import (
    _get_float,
    _get_int,
    validate_scenario_parameters,
)

BASE_CONFIG = {
    "scenarios": {
        "temperature": {"min_delta": -5.0, "max_delta": 5.0},
        "rainfall": {"min_percent_change": -100.0, "max_percent_change": 500.0},
        "monsoon": {
            "max_delay_days": 30,
            "max_advance_days": 15,
            "intensity_reduction_range": [0, 50],
        },
        "extreme_events": {"enabled": True, "types": ["flood", "heatwave", "drought"]},
    },
    "validation": {"max_combined_scenarios": 5},
}


@pytest.fixture(autouse=True)
def patch_config():
    from simulator.validators import scenario_validator as sv

    sv._SCENARIO_CONFIG = BASE_CONFIG
    yield
    sv._SCENARIO_CONFIG = None


class TestValidateTemperature:
    def test_missing_delta(self):
        errors = validate_scenario_parameters("temperature", {})
        assert "temperature_delta is required" in errors

    def test_out_of_range(self):
        errors = validate_scenario_parameters("temperature", {"temperature_delta": 10.0})
        assert any("out of range" in e for e in errors)

    def test_valid(self):
        errors = validate_scenario_parameters("temperature", {"temperature_delta": 2.0})
        assert errors == []


class TestValidateRainfall:
    def test_missing_pct(self):
        errors = validate_scenario_parameters("rainfall", {})
        assert "rainfall_change_pct is required" in errors

    def test_out_of_range(self):
        errors = validate_scenario_parameters("rainfall", {"rainfall_change_pct": 1000.0})
        assert any("out of range" in e for e in errors)

    def test_valid(self):
        errors = validate_scenario_parameters("rainfall", {"rainfall_change_pct": 50.0})
        assert errors == []


class TestValidateMonsoon:
    def test_missing_delay(self):
        errors = validate_scenario_parameters("monsoon", {})
        assert "delay_days is required" in errors

    def test_delay_out_of_range(self):
        errors = validate_scenario_parameters("monsoon", {"delay_days": 100})
        assert any("out of range" in e for e in errors)

    def test_intensity_out_of_range(self):
        errors = validate_scenario_parameters(
            "monsoon", {"delay_days": 5, "intensity_reduction_pct": 200}
        )
        assert any("out of range" in e for e in errors)

    def test_valid(self):
        errors = validate_scenario_parameters("monsoon", {"delay_days": 5})
        assert errors == []


class TestValidateExtremeEvent:
    def test_unsupported_type(self):
        errors = validate_scenario_parameters("extreme_event", {"event_type": "tornado"})
        assert any("Unsupported extreme event type" in e for e in errors)

    def test_valid_type(self):
        errors = validate_scenario_parameters("extreme_event", {"event_type": "flood"})
        assert errors == []


class TestValidateExtremeEventDisabled:
    def test_disabled(self):
        from simulator.validators import scenario_validator as sv

        sv._SCENARIO_CONFIG = {
            "scenarios": {
                "extreme_events": {"enabled": False, "types": ["flood", "heatwave", "drought"]},
            },
            "validation": {"max_combined_scenarios": 5},
        }
        errors = validate_scenario_parameters("extreme_event", {"event_type": "flood"})
        assert "Extreme events are disabled" in errors


class TestValidateCombined:
    def test_max_exceeded(self):
        scenarios = [
            {"scenario_type": "temperature", "parameters": {"temperature_delta": 1.0}}
        ] * 10
        errors = validate_scenario_parameters("combined", {"scenarios": scenarios})
        assert any("Too many combined" in e for e in errors)

    def test_scenarios_not_a_list(self):
        errors = validate_scenario_parameters("combined", {"scenarios": "not_a_list"})
        assert any("requires a list" in e for e in errors)

    def test_sub_scenario_not_a_dict(self):
        errors = validate_scenario_parameters("combined", {"scenarios": ["not_a_dict"]})
        assert any("is not a dict" in e for e in errors)

    def test_valid(self):
        valid = {
            "scenarios": [
                {"scenario_type": "temperature", "parameters": {"temperature_delta": 1.0}},
            ]
        }
        errors = validate_scenario_parameters("combined", valid)
        assert errors == []


class TestUnsupportedType:
    def test_unsupported(self):
        errors = validate_scenario_parameters("unknown_type", {})
        assert any("Unsupported scenario type" in e for e in errors)


class TestGetFloat:
    def test_none(self):
        assert _get_float({}, "missing") is None

    def test_valid(self):
        assert _get_float({"x": 5.0}, "x") == 5.0

    def test_conversion_failure(self):
        assert _get_float({"x": "not_a_number"}, "x") is None
        assert _get_float({"x": [1, 2]}, "x") is None


class TestGetInt:
    def test_none(self):
        assert _get_int({}, "missing") is None

    def test_valid(self):
        assert _get_int({"x": 5}, "x") == 5

    def test_conversion_failure(self):
        assert _get_int({"x": "not_an_int"}, "x") is None
        assert _get_int({"x": [1, 2]}, "x") is None
