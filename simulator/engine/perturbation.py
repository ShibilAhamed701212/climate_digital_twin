"""Perturbation engine for applying climate perturbations to weather data.

Supports temperature deltas, precipitation multipliers, humidity/wind/pressure
deltas, with constant, time-varying, diurnal, and seasonal patterns.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from simulator.models.scenario_models import ScenarioDefinition
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)

# WeatherObservation field names that can be perturbed
_OBSERVATION_FIELDS = {
    "temperature_2m": "temperature_delta",
    "precipitation_mm": "rainfall_multiplier",
    "humidity_pct": "humidity_delta",
    "wind_speed_10m": "wind_speed_delta",
    "pressure_hpa": "pressure_delta",
}

# Mapping from parameter key to perturbation type
_DELTA_FIELDS = {"temperature_delta", "humidity_delta", "wind_speed_delta", "pressure_delta"}
_MULTIPLIER_FIELDS = {"rainfall_multiplier"}


class PerturbationEngine:
    """Applies climate perturbations to weather/forecast data.

    Supports:
    - Temperature delta (+/- C)
    - Precipitation multiplier (e.g., 1.2 for +20%)
    - Humidity delta (+/- %)
    - Wind speed delta (+/- m/s)
    - Pressure delta (+/- hPa)
    - Custom parameter perturbations

    Perturbation can be:
    - Constant (uniform across all time steps)
    - Time-varying (e.g., ramp up over duration)
    - Diurnal (different day/night effects)
    - Seasonal (different effects by season)
    """

    def __init__(self, pattern: str = "constant") -> None:
        valid_patterns = {"constant", "ramp", "diurnal", "seasonal"}
        if pattern not in valid_patterns:
            raise ValueError(f"Unknown pattern '{pattern}'. Valid: {valid_patterns}")
        self._pattern = pattern
        _logger.debug("PerturbationEngine initialized with pattern='%s'", pattern)

    @property
    def pattern(self) -> str:
        return self._pattern

    def apply_perturbation(
        self,
        observations: list[WeatherObservation],
        scenario: ScenarioDefinition,
    ) -> list[WeatherObservation]:
        if not observations:
            raise ValueError("Cannot perturb empty observations list")

        hours = (
            [obs.timestamp.hour for obs in observations] if self._pattern in ("diurnal",) else None
        )
        months = (
            [obs.timestamp.month for obs in observations]
            if self._pattern in ("seasonal",)
            else None
        )

        params = scenario.parameters
        temp_delta = params.get("temperature_delta")
        rain_mult = params.get("rainfall_multiplier")
        humid_delta = params.get("humidity_delta")
        press_delta = params.get("pressure_delta")
        wind_delta = params.get("wind_speed_delta")

        perturbed: list[WeatherObservation] = []
        for i, obs in enumerate(observations):
            factor = self._get_time_factor(
                i, len(observations), hours[i] if hours else 0, months[i] if months else 0
            )

            new_obs = WeatherObservation(
                location_id=obs.location_id,
                latitude=obs.latitude,
                longitude=obs.longitude,
                timestamp=obs.timestamp,
                temperature_2m=self._apply_delta(obs.temperature_2m, temp_delta, factor),
                precipitation_mm=self._apply_multiplier(obs.precipitation_mm, rain_mult, factor),
                humidity_pct=self._apply_delta(obs.humidity_pct, humid_delta, factor),
                pressure_hpa=self._apply_delta(obs.pressure_hpa, press_delta, factor),
                wind_speed_10m=self._apply_delta(obs.wind_speed_10m, wind_delta, factor),
                wind_direction_10m=obs.wind_direction_10m,
                solar_radiation=obs.solar_radiation,
                cloud_cover_pct=obs.cloud_cover_pct,
                soil_moisture=obs.soil_moisture,
                data_source=obs.data_source,
                quality_flag=obs.quality_flag,
            )
            perturbed.append(new_obs)

        if scenario.parameters:
            param_perturbed = self._apply_custom_parameters(perturbed, scenario)
            perturbed = param_perturbed

        _logger.debug(
            "Applied %s perturbation to %d observations (scenario=%s)",
            self._pattern,
            len(observations),
            scenario.scenario_id,
        )
        return perturbed

    def apply_to_timeseries(
        self,
        time_series: dict[str, list[float]],
        scenario: ScenarioDefinition,
    ) -> dict[str, list[float]]:
        if not time_series:
            raise ValueError("Cannot perturb empty time series")

        n_steps = max(len(v) for v in time_series.values())
        perturbed: dict[str, list[float]] = {}

        for var_name, values in time_series.items():
            perturbed_values: list[float] = []
            for i, val in enumerate(values):
                factor = self._get_time_factor(i, n_steps, 0, 0)
                perturbed_val = self._apply_perturbation_to_variable(
                    val, var_name, scenario, factor
                )
                perturbed_values.append(perturbed_val)
            perturbed[var_name] = perturbed_values

        return perturbed

    def get_perturbed_summary(
        self,
        base_summary: dict[str, float],
        scenario: ScenarioDefinition,
    ) -> dict[str, float]:
        perturbed: dict[str, float] = {}
        for key, value in base_summary.items():
            perturbed[key] = self._apply_perturbation_to_variable(value, key, scenario, 1.0)
        return perturbed

    @staticmethod
    def compute_deltas(base: list[float], perturbed: list[float]) -> dict[str, float]:
        base_arr = np.array(base, dtype=np.float64)
        perturbed_arr = np.array(perturbed, dtype=np.float64)
        deltas = perturbed_arr - base_arr

        return {
            "mean_delta": float(np.mean(deltas)),
            "max_delta": float(np.max(deltas)),
            "min_delta": float(np.min(deltas)),
            "std_delta": float(np.std(deltas)),
            "mean_abs_delta": float(np.mean(np.abs(deltas))),
            "max_abs_delta": float(np.max(np.abs(deltas))),
        }

    @staticmethod
    def _apply_diurnal_pattern(
        base_values: np.ndarray,
        hour_of_day: list[int],
        delta: float,
    ) -> np.ndarray:
        if delta == 0.0:
            return base_values.copy()

        hours = np.array(hour_of_day, dtype=np.float64)
        diurnal_factor = 1.0 + 0.7 * np.cos((hours - 13.0) * np.pi / 12.0)
        effective_delta = delta * diurnal_factor
        return base_values + effective_delta

    @staticmethod
    def _apply_seasonal_pattern(
        base_values: np.ndarray,
        month: list[int],
        delta: float,
    ) -> np.ndarray:
        if delta == 0.0:
            return base_values.copy()

        months = np.array(month, dtype=np.float64)
        seasonal_factor = 1.0 + 0.5 * np.cos((months - 7.0) * np.pi / 6.0)
        effective_delta = delta * seasonal_factor
        return base_values + effective_delta

    def _get_time_factor(self, index: int, total: int, hour: int, month: int) -> float:
        if self._pattern == "ramp":
            if total <= 1:
                return 1.0
            progress = index / (total - 1)
            return 0.5 + progress

        if self._pattern == "diurnal":
            diurnal = 1.0 + 0.7 * np.cos((hour - 13.0) * np.pi / 12.0)
            return float(diurnal)

        if self._pattern == "seasonal":
            seasonal = 1.0 + 0.5 * np.cos((month - 7.0) * np.pi / 6.0)
            return float(seasonal)

        return 1.0

    @staticmethod
    def _apply_delta(value: float, delta: float | None, factor: float) -> float:
        if delta is None or delta == 0.0:
            return value
        return value + delta * factor

    @staticmethod
    def _apply_multiplier(value: float, multiplier: float | None, factor: float) -> float:
        if multiplier is None or multiplier == 1.0:
            return value
        effective_mult = 1.0 + (multiplier - 1.0) * factor
        result = value * effective_mult
        return max(0.0, result)

    @staticmethod
    def _apply_perturbation_to_variable(
        value: float,
        var_name: str,
        scenario: ScenarioDefinition,
        factor: float,
    ) -> float:
        params = scenario.parameters
        if "temperature" in var_name:
            delta = params.get("temperature_delta")
            if delta is not None:
                return value + delta * factor
        if "precip" in var_name:
            mult = params.get("rainfall_multiplier")
            if mult is not None:
                effective_mult = 1.0 + (mult - 1.0) * factor
                return max(0.0, value * effective_mult)
        if "humid" in var_name:
            delta = params.get("humidity_delta")
            if delta is not None:
                return value + delta * factor
        if "wind" in var_name:
            delta = params.get("wind_speed_delta")
            if delta is not None:
                return value + delta * factor
        if "pressure" in var_name:
            delta = params.get("pressure_delta")
            if delta is not None:
                return value + delta * factor
        return value

    @staticmethod
    def _apply_custom_parameters(
        observations: list[WeatherObservation],
        scenario: ScenarioDefinition,
    ) -> list[WeatherObservation]:
        if not scenario.parameters:
            return observations

        param_map: dict[str, Any] = {}
        offset_params: dict[str, float] = {}
        factor_params: dict[str, float] = {}

        for key, val in scenario.parameters.items():
            if isinstance(val, int | float):
                if "_offset" in key:
                    var_key = key.replace("_offset", "")
                    offset_params[var_key] = val
                elif "_factor" in key:
                    var_key = key.replace("_factor", "")
                    factor_params[var_key] = val
                else:
                    param_map[key] = val

        if not offset_params and not factor_params:
            return observations

        perturbed: list[WeatherObservation] = []
        for obs in observations:
            new_temp = obs.temperature_2m
            new_precip = obs.precipitation_mm
            new_humid = obs.humidity_pct
            new_pressure = obs.pressure_hpa
            new_wind = obs.wind_speed_10m

            for var_key, offset in offset_params.items():
                if "temp" in var_key:
                    new_temp += offset
                elif "precip" in var_key:
                    new_precip = max(0.0, new_precip + offset)
                elif "humid" in var_key:
                    new_humid += offset
                elif "press" in var_key:
                    new_pressure += offset
                elif "wind" in var_key:
                    new_wind += offset

            for var_key, factor in factor_params.items():
                if "temp" in var_key:
                    new_temp *= factor
                elif "precip" in var_key:
                    new_precip = max(0.0, new_precip * factor)
                elif "humid" in var_key:
                    new_humid *= factor
                elif "press" in var_key:
                    new_pressure *= factor
                elif "wind" in var_key:
                    new_wind *= factor

            perturbed.append(
                WeatherObservation(
                    location_id=obs.location_id,
                    latitude=obs.latitude,
                    longitude=obs.longitude,
                    timestamp=obs.timestamp,
                    temperature_2m=new_temp,
                    precipitation_mm=new_precip,
                    humidity_pct=new_humid,
                    pressure_hpa=new_pressure,
                    wind_speed_10m=new_wind,
                    wind_direction_10m=obs.wind_direction_10m,
                    solar_radiation=obs.solar_radiation,
                    cloud_cover_pct=obs.cloud_cover_pct,
                    soil_moisture=obs.soil_moisture,
                    data_source=obs.data_source,
                    quality_flag=obs.quality_flag,
                )
            )

        return perturbed


__all__ = [
    "PerturbationEngine",
]
