"""Unit tests for scenario parameter validation."""

from __future__ import annotations


class TestTemperatureValidation:
    """Test temperature scenario validation."""

    def test_valid_temperature_delta(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {"temperature_delta": 2.0})
        assert errors == []

    def test_valid_negative_delta(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {"temperature_delta": -2.0})
        assert errors == []

    def test_invalid_delta_too_high(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {"temperature_delta": 10.0})
        assert len(errors) > 0
        assert "out of range" in errors[0]

    def test_invalid_delta_too_low(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {"temperature_delta": -10.0})
        assert len(errors) > 0

    def test_missing_temperature_delta(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {})
        assert any("temperature_delta" in e for e in errors)

    def test_zero_delta(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("temperature", {"temperature_delta": 0.0})
        assert errors == []


class TestRainfallValidation:
    """Test rainfall scenario validation."""

    def test_valid_increase(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("rainfall", {"rainfall_change_pct": 20.0})
        assert errors == []

    def test_valid_decrease(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("rainfall", {"rainfall_change_pct": -50.0})
        assert errors == []

    def test_invalid_below_minimum(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("rainfall", {"rainfall_change_pct": -200.0})
        assert len(errors) > 0

    def test_missing_parameter(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("rainfall", {})
        assert any("rainfall_change_pct" in e for e in errors)


class TestMonsoonValidation:
    """Test monsoon scenario validation."""

    def test_valid_delay(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "monsoon", {"delay_days": 15, "intensity_reduction_pct": 20.0}
        )
        assert errors == []

    def test_valid_early(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "monsoon", {"delay_days": -7}
        )
        assert errors == []

    def test_invalid_delay_too_large(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("monsoon", {"delay_days": 60})
        assert len(errors) > 0

    def test_missing_delay(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("monsoon", {})
        assert any("delay_days" in e for e in errors)

    def test_invalid_intensity(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "monsoon", {"delay_days": 10, "intensity_reduction_pct": 100.0}
        )
        assert len(errors) > 0


class TestExtremeEventValidation:
    """Test extreme event scenario validation."""

    def test_valid_heatwave(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "extreme_event", {"event_type": "heatwave"}
        )
        assert errors == []

    def test_valid_flood(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "extreme_event", {"event_type": "flood"}
        )
        assert errors == []

    def test_valid_drought(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "extreme_event", {"event_type": "drought"}
        )
        assert errors == []

    def test_invalid_event_type(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters(
            "extreme_event", {"event_type": "tornado"}
        )
        assert len(errors) > 0

    def test_missing_event_type(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("extreme_event", {})
        assert len(errors) > 0


class TestCombinedValidation:
    """Test combined scenario validation."""

    def test_valid_combined(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("combined", {
            "scenarios": [
                {"scenario_type": "temperature", "parameters": {"temperature_delta": 2.0}},
                {"scenario_type": "rainfall", "parameters": {"rainfall_change_pct": 20.0}},
            ],
        })
        assert errors == []

    def test_too_many_combined(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("combined", {
            "scenarios": [
                {"scenario_type": "temperature", "parameters": {"temperature_delta": 1.0}}
                for _ in range(10)
            ],
        })
        assert len(errors) > 0

    def test_invalid_sub_scenario(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("combined", {
            "scenarios": [
                {"scenario_type": "temperature", "parameters": {"temperature_delta": 100.0}},
            ],
        })
        assert len(errors) > 0


class TestUnknownType:
    """Test unknown scenario type validation."""

    def test_unknown_type(self):
        from simulator.validators.scenario_validator import validate_scenario_parameters

        errors = validate_scenario_parameters("unknown_type", {})
        assert len(errors) > 0
        assert "Unsupported" in errors[0]
