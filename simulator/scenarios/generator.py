"""Scenario generator for predefined climate scenario definitions.

Provides IPCC-based warming scenarios, rainfall change scenarios,
extreme event scenarios, and custom scenario creation with validation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from simulator.models.scenario_models import ScenarioDefinition

_logger = logging.getLogger(__name__)

# IPCC SSP warming levels by year (global mean temperature change in C)
# Source: IPCC AR6 WG1 Summary for Policymakers
_IPCC_WARMING_LEVELS: dict[str, dict[int, float]] = {
    "ssp119": {2030: 1.0, 2050: 1.2, 2100: 1.0},
    "ssp126": {2030: 1.1, 2050: 1.4, 2100: 1.8},
    "ssp245": {2030: 1.2, 2050: 1.8, 2100: 2.7},
    "ssp370": {2030: 1.3, 2050: 2.0, 2100: 3.6},
    "ssp585": {2030: 1.4, 2050: 2.3, 2100: 4.4},
}

_VALID_PATHWAYS = set(_IPCC_WARMING_LEVELS.keys())

_DEFAULT_DURATIONS: dict[str, int] = {
    "temperature": 30,
    "rainfall": 30,
    "extreme_event": 14,
    "monsoon_shift": 90,
    "combined": 30,
    "custom": 30,
}


def _generate_id() -> str:
    return f"scenario_{uuid.uuid4().hex[:8]}"


class ScenarioGenerator:
    def warming_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        delta_c: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name=f"+{delta_c}C Warming",
            description=f"Temperature increase of {delta_c}C at {location_id}",
            scenario_type="temperature",
            parameters={
                "temperature_delta": delta_c,
                "location_id": location_id,
                "latitude": latitude,
                "longitude": longitude,
                "duration_days": duration_days,
                "warming_rate": delta_c / duration_days,
            },
        )

    def rainfall_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        multiplier: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        pct = int(round((multiplier - 1.0) * 100))
        sign = "+" if pct >= 0 else ""
        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name=f"{sign}{pct}% Rainfall Change",
            description=f"Rainfall {sign}{pct}% change at {location_id}",
            scenario_type="rainfall",
            parameters={
                "rainfall_multiplier": multiplier,
                "location_id": location_id,
                "latitude": latitude,
                "longitude": longitude,
                "duration_days": duration_days,
                "rainfall_change_pct": float(pct),
            },
        )

    def extreme_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name="Extreme Worst-Case",
            description=f"Extreme scenario: +4C warming + 30% more rainfall at {location_id}",
            scenario_type="extreme_event",
            parameters={
                "temperature_delta": 4.0,
                "rainfall_multiplier": 1.3,
                "humidity_delta": 5.0,
                "location_id": location_id,
                "latitude": latitude,
                "longitude": longitude,
                "duration_days": duration_days,
                "warming_rate": 4.0 / duration_days,
                "rainfall_change_pct": 30.0,
            },
        )

    def drought_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        duration_days: int = 90,
    ) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name="Drought Conditions",
            description=f"Drought scenario: +2C warming + 20% less rainfall at {location_id}",
            scenario_type="extreme_event",
            parameters={
                "temperature_delta": 2.0,
                "rainfall_multiplier": 0.8,
                "humidity_delta": -5.0,
                "location_id": location_id,
                "latitude": latitude,
                "longitude": longitude,
                "duration_days": duration_days,
                "warming_rate": 2.0 / duration_days,
                "rainfall_change_pct": -20.0,
                "drought_intensity": 0.6,
            },
        )

    def ipcc_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        pathway: str = "ssp585",
        year: int = 2050,
    ) -> ScenarioDefinition:
        pathway_lower = pathway.lower()
        if pathway_lower not in _VALID_PATHWAYS:
            raise ValueError(f"Unknown pathway '{pathway}'. Valid: {sorted(_VALID_PATHWAYS)}")

        warming_levels = _IPCC_WARMING_LEVELS[pathway_lower]
        available_years = sorted(warming_levels.keys())
        closest_year = min(available_years, key=lambda y: abs(y - year))
        delta_c = warming_levels[closest_year]

        years_from_now = max(1, year - datetime.now(UTC).year)
        duration_days = years_from_now * 365 // 12

        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name=f"IPCC {pathway.upper()} ({year})",
            description=(
                f"IPCC {pathway.upper()} scenario for {year} at {location_id}. "
                f"~{delta_c:.1f}C warming (based on {closest_year} projections)."
            ),
            scenario_type="temperature",
            parameters={
                "temperature_delta": delta_c,
                "location_id": location_id,
                "latitude": latitude,
                "longitude": longitude,
                "duration_days": min(duration_days, 365),
                "target_year": float(year),
                "closest_year": float(closest_year),
            },
        )

    def custom_scenario(
        self,
        name: str,
        description: str,
        location_id: str,
        latitude: float,
        longitude: float,
        parameters: dict[str, Any],
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        _temperature_delta = parameters.get("temperature_delta")
        _rainfall_multiplier = parameters.get("rainfall_multiplier")
        _humidity_delta = parameters.get("humidity_delta")
        _wind_speed_delta = parameters.get("wind_speed_delta")
        _pressure_delta = parameters.get("pressure_delta")

        scenario_type = self._infer_scenario_type(parameters)

        standard_keys = {
            "temperature_delta",
            "rainfall_multiplier",
            "humidity_delta",
            "wind_speed_delta",
            "pressure_delta",
        }
        merged: dict[str, Any] = {
            "location_id": location_id,
            "latitude": latitude,
            "longitude": longitude,
            "duration_days": duration_days,
        }
        for k, v in parameters.items():
            if k not in standard_keys and not isinstance(v, int | float | str):
                continue
            merged[k] = v

        return ScenarioDefinition(
            scenario_id=_generate_id(),
            name=name,
            description=description,
            scenario_type=scenario_type,
            parameters=merged,
        )

    def validate_scenario(self, scenario: ScenarioDefinition) -> list[str]:
        issues: list[str] = []
        params = scenario.parameters

        lat = params.get("latitude")
        if lat is not None and not -90.0 <= lat <= 90.0:
            issues.append(f"Latitude {lat} out of range [-90, 90]")
        lon = params.get("longitude")
        if lon is not None and not -180.0 <= lon <= 180.0:
            issues.append(f"Longitude {lon} out of range [-180, 180]")

        duration = params.get("duration_days", 30)
        if isinstance(duration, int | float):
            if duration <= 0:
                issues.append(f"Duration {duration} must be positive")
            if duration > 3650:
                issues.append(f"Duration {duration} exceeds 10-year maximum")

        temp_delta = params.get("temperature_delta")
        if temp_delta is not None and (temp_delta < -20.0 or temp_delta > 20.0):
            issues.append(f"Temperature delta {temp_delta}C is unrealistic")

        rain_mult = params.get("rainfall_multiplier")
        if rain_mult is not None:
            if rain_mult <= 0:
                issues.append(f"Rainfall multiplier {rain_mult} must be positive")
            if rain_mult > 5.0:
                issues.append(f"Rainfall multiplier {rain_mult} > 5x is unrealistic")

        humid_delta = params.get("humidity_delta")
        if humid_delta is not None and (humid_delta < -100 or humid_delta > 100):
            issues.append(f"Humidity delta {humid_delta}% is unrealistic")

        wind_delta = params.get("wind_speed_delta")
        if wind_delta is not None and abs(wind_delta) > 50:
            issues.append(f"Wind speed delta {wind_delta} m/s is unrealistic")

        press_delta = params.get("pressure_delta")
        if press_delta is not None and abs(press_delta) > 50:
            issues.append(f"Pressure delta {press_delta} hPa is unrealistic")

        if scenario.scenario_type == "temperature" and temp_delta is None:
            issues.append("Temperature scenario without temperature_delta parameter")

        if scenario.scenario_type == "rainfall" and rain_mult is None:
            issues.append("Rainfall scenario without rainfall_multiplier parameter")

        return issues

    @staticmethod
    def list_pathways() -> list[str]:
        return sorted(_VALID_PATHWAYS)

    @staticmethod
    def get_warming_level(pathway: str, year: int) -> float | None:
        pathway_lower = pathway.lower()
        if pathway_lower not in _IPCC_WARMING_LEVELS:
            return None
        levels = _IPCC_WARMING_LEVELS[pathway_lower]
        available_years = sorted(levels.keys())
        closest_year = min(available_years, key=lambda y: abs(y - year))
        return levels[closest_year]

    @staticmethod
    def _infer_scenario_type(parameters: dict[str, Any]) -> str:
        has_temp = "temperature_delta" in parameters
        has_rain = "rainfall_multiplier" in parameters
        has_other = any(
            k in parameters for k in ["humidity_delta", "wind_speed_delta", "pressure_delta"]
        )

        if has_temp and has_rain:
            return "combined"
        if has_temp:
            return "temperature"
        if has_rain:
            return "rainfall"
        if has_other:
            return "custom"
        return "custom"

    @staticmethod
    def estimate_end_date(scenario: ScenarioDefinition) -> datetime:
        duration = scenario.parameters.get("duration_days", 30)
        if isinstance(duration, int | float):
            return datetime.now(UTC) + timedelta(days=int(duration))
        return datetime.now(UTC) + timedelta(days=30)

    @staticmethod
    def get_default_duration(scenario_type: str) -> int:
        return _DEFAULT_DURATIONS.get(scenario_type, 30)


__all__ = [
    "ScenarioGenerator",
]
