from datetime import UTC, datetime

import numpy as np
import pytest

from simulator.engine.perturbation import PerturbationEngine
from simulator.models.scenario_models import ScenarioDefinition
from simulator.models.weather import WeatherObservation


def make_obs(
    temp=25.0,
    precip=0.0,
    humid=50.0,
    press=1013.0,
    wind=5.0,
    wdir=180.0,
    hour=12,
    month=1,
    loc="loc1",
):
    return WeatherObservation(
        location_id=loc,
        latitude=10.0,
        longitude=20.0,
        timestamp=datetime(2020, month, 1, hour, 0, 0, tzinfo=UTC),
        temperature_2m=temp,
        precipitation_mm=precip,
        humidity_pct=humid,
        pressure_hpa=press,
        wind_speed_10m=wind,
        wind_direction_10m=wdir,
    )


def scenario(params=None):
    return ScenarioDefinition(
        scenario_id="test",
        name="Test",
        description="",
        scenario_type="test",
        parameters=params or {},
    )


class TestInit:
    def test_valid_patterns(self):
        for p in ("constant", "ramp", "diurnal", "seasonal"):
            eng = PerturbationEngine(p)
            assert eng.pattern == p

    def test_invalid_pattern(self):
        with pytest.raises(ValueError, match="Unknown pattern"):
            PerturbationEngine("invalid")


class TestApplyDelta:
    def test_no_delta(self):
        assert PerturbationEngine._apply_delta(25.0, None, 1.0) == 25.0
        assert PerturbationEngine._apply_delta(25.0, 0.0, 1.0) == 25.0

    def test_with_delta(self):
        assert PerturbationEngine._apply_delta(25.0, 2.0, 1.0) == 27.0

    def test_with_factor(self):
        assert PerturbationEngine._apply_delta(25.0, 2.0, 0.5) == 26.0


class TestApplyMultiplier:
    def test_no_multiplier(self):
        assert PerturbationEngine._apply_multiplier(10.0, None, 1.0) == 10.0
        assert PerturbationEngine._apply_multiplier(10.0, 1.0, 1.0) == 10.0

    def test_with_multiplier(self):
        result = PerturbationEngine._apply_multiplier(10.0, 1.2, 1.0)
        assert result == pytest.approx(12.0)

    def test_with_factor(self):
        result = PerturbationEngine._apply_multiplier(10.0, 1.2, 0.5)
        assert result == pytest.approx(11.0)

    def test_clamps_to_zero(self):
        result = PerturbationEngine._apply_multiplier(10.0, -1.0, 1.0)
        assert result == 0.0


class TestTimeFactor:
    def test_constant(self):
        eng = PerturbationEngine("constant")
        assert eng._get_time_factor(0, 10, 12, 1) == 1.0

    def test_ramp(self):
        eng = PerturbationEngine("ramp")
        assert eng._get_time_factor(0, 10, 0, 0) == 0.5
        assert eng._get_time_factor(9, 10, 0, 0) == 1.5

    def test_ramp_single(self):
        eng = PerturbationEngine("ramp")
        assert eng._get_time_factor(0, 1, 0, 0) == 1.0

    def test_diurnal(self):
        eng = PerturbationEngine("diurnal")
        factor = eng._get_time_factor(0, 10, 13, 0)
        assert factor == pytest.approx(1.7)

    def test_seasonal(self):
        eng = PerturbationEngine("seasonal")
        factor = eng._get_time_factor(0, 10, 0, 7)
        assert factor == pytest.approx(1.5)


class TestApplyPerturbation:
    def test_constant_temperature(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0), make_obs(temp=30.0)]
        s = scenario({"temperature_delta": 3.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == 28.0
        assert result[1].temperature_2m == 33.0

    def test_constant_rainfall(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(precip=10.0)]
        s = scenario({"rainfall_multiplier": 1.5})
        result = eng.apply_perturbation(obs, s)
        assert result[0].precipitation_mm == 15.0

    def test_constant_humidity(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(humid=50.0)]
        s = scenario({"humidity_delta": -5.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].humidity_pct == 45.0

    def test_constant_pressure(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(press=1013.0)]
        s = scenario({"pressure_delta": 2.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].pressure_hpa == 1015.0

    def test_constant_wind(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(wind=5.0)]
        s = scenario({"wind_speed_delta": 1.5})
        result = eng.apply_perturbation(obs, s)
        assert result[0].wind_speed_10m == 6.5

    def test_ramp_pattern(self):
        eng = PerturbationEngine("ramp")
        obs = [make_obs(temp=20.0), make_obs(temp=20.0)]
        s = scenario({"temperature_delta": 2.0})
        result = eng.apply_perturbation(obs, s)
        first_delta = result[0].temperature_2m - 20.0
        second_delta = result[1].temperature_2m - 20.0
        assert first_delta < second_delta

    def test_empty_observations_raises(self):
        eng = PerturbationEngine("constant")
        s = scenario({"temperature_delta": 1.0})
        with pytest.raises(ValueError, match="empty"):
            eng.apply_perturbation([], s)

    def test_no_parameters(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0)]
        s = scenario({})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == 25.0

    def test_preserves_other_fields(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0, precip=10.0, humid=50.0, press=1013.0, wind=5.0, wdir=180.0)]
        s = scenario({"temperature_delta": 1.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == 26.0
        assert result[0].precipitation_mm == 10.0
        assert result[0].wind_direction_10m == 180.0


class TestApplyToTimeseries:
    def test_basic(self):
        eng = PerturbationEngine("constant")
        ts = {"temperature_2m": [20.0, 25.0, 30.0]}
        s = scenario({"temperature_delta": 2.0})
        result = eng.apply_to_timeseries(ts, s)
        assert result["temperature_2m"] == [22.0, 27.0, 32.0]

    def test_empty_raises(self):
        eng = PerturbationEngine("constant")
        s = scenario({"temperature_delta": 1.0})
        with pytest.raises(ValueError, match="empty"):
            eng.apply_to_timeseries({}, s)


class TestGetPerturbedSummary:
    def test_basic(self):
        eng = PerturbationEngine("constant")
        summary = {"temperature_2m": 25.0}
        s = scenario({"temperature_delta": 3.0})
        result = eng.get_perturbed_summary(summary, s)
        assert result["temperature_2m"] == 28.0


class TestComputeDeltas:
    def test_basic(self):
        base = [10.0, 20.0, 30.0]
        perturbed = [12.0, 22.0, 32.0]
        result = PerturbationEngine.compute_deltas(base, perturbed)
        assert result["mean_delta"] == 2.0
        assert result["max_delta"] == 2.0
        assert result["min_delta"] == 2.0

    def test_varied(self):
        base = [10.0, 20.0, 30.0]
        perturbed = [15.0, 22.0, 25.0]
        result = PerturbationEngine.compute_deltas(base, perturbed)
        assert result["mean_delta"] == pytest.approx(0.6667, rel=0.01)
        assert result["max_delta"] == 5.0
        assert result["min_delta"] == -5.0


class TestDiurnalPattern:
    def test_zero_delta(self):
        result = PerturbationEngine._apply_diurnal_pattern(np.array([20.0, 25.0]), [12, 14], 0.0)
        assert np.allclose(result, [20.0, 25.0])

    def test_with_delta(self):
        result = PerturbationEngine._apply_diurnal_pattern(np.array([20.0]), [13], 2.0)
        assert result[0] == pytest.approx(23.4, rel=0.01)


class TestSeasonalPattern:
    def test_zero_delta(self):
        result = PerturbationEngine._apply_seasonal_pattern(np.array([20.0, 25.0]), [1, 7], 0.0)
        assert np.allclose(result, [20.0, 25.0])

    def test_with_delta(self):
        result = PerturbationEngine._apply_seasonal_pattern(np.array([20.0]), [7], 2.0)
        assert result[0] == pytest.approx(23.0, rel=0.01)


class TestCustomParameters:
    def test_offset_params(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0, precip=10.0)]
        s = scenario({"temp_offset": 2.0, "precip_offset": 3.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == 27.0
        assert result[0].precipitation_mm == 13.0

    def test_factor_params(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0, precip=10.0)]
        s = scenario({"temp_factor": 1.1, "precip_factor": 0.5})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == pytest.approx(27.5)
        assert result[0].precipitation_mm == 5.0

    def test_custom_only_standard_params(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0)]
        s = scenario({"some_other_param": 42.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].temperature_2m == 25.0

    def test_no_custom_params(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(temp=25.0)]
        s = scenario({})
        result = eng.apply_perturbation(obs, s)
        assert len(result) == 1

    def test_apply_custom_parameters_empty_params(self):
        obs = [make_obs(temp=25.0)]
        s = scenario({})
        result = PerturbationEngine._apply_custom_parameters(obs, s)
        assert result == obs

    def test_humid_offset(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(humid=50.0)]
        s = scenario({"humid_offset": 10.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].humidity_pct == 60.0

    def test_pressure_offset(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(press=1013.0)]
        s = scenario({"press_offset": 5.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].pressure_hpa == 1018.0

    def test_wind_offset(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(wind=5.0)]
        s = scenario({"wind_offset": 2.0})
        result = eng.apply_perturbation(obs, s)
        assert result[0].wind_speed_10m == 7.0

    def test_humid_factor(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(humid=50.0)]
        s = scenario({"humid_factor": 1.2})
        result = eng.apply_perturbation(obs, s)
        assert result[0].humidity_pct == 60.0

    def test_pressure_factor(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(press=1013.0)]
        s = scenario({"press_factor": 1.01})
        result = eng.apply_perturbation(obs, s)
        assert result[0].pressure_hpa == pytest.approx(1023.13)

    def test_wind_factor(self):
        eng = PerturbationEngine("constant")
        obs = [make_obs(wind=5.0)]
        s = scenario({"wind_factor": 1.5})
        result = eng.apply_perturbation(obs, s)
        assert result[0].wind_speed_10m == 7.5


class TestApplyPerturbationToVariable:
    def test_temperature(self):
        s = scenario({"temperature_delta": 2.0})
        result = PerturbationEngine._apply_perturbation_to_variable(25.0, "temperature_2m", s, 1.0)
        assert result == 27.0

    def test_precipitation(self):
        s = scenario({"rainfall_multiplier": 1.5})
        result = PerturbationEngine._apply_perturbation_to_variable(
            10.0, "precipitation_mm", s, 1.0
        )
        assert result == 15.0

    def test_humidity(self):
        s = scenario({"humidity_delta": -3.0})
        result = PerturbationEngine._apply_perturbation_to_variable(50.0, "humidity_pct", s, 1.0)
        assert result == 47.0

    def test_wind(self):
        s = scenario({"wind_speed_delta": 2.0})
        result = PerturbationEngine._apply_perturbation_to_variable(5.0, "wind_speed_10m", s, 1.0)
        assert result == 7.0

    def test_pressure(self):
        s = scenario({"pressure_delta": -5.0})
        result = PerturbationEngine._apply_perturbation_to_variable(1013.0, "pressure_hpa", s, 1.0)
        assert result == 1008.0

    def test_unknown_variable(self):
        s = scenario({})
        result = PerturbationEngine._apply_perturbation_to_variable(25.0, "unknown_var", s, 1.0)
        assert result == 25.0
