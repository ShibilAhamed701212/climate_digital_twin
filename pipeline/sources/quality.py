from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)

MIN_TEMPERATURE_C = -50.0
MAX_TEMPERATURE_C = 60.0
MIN_PRECIPITATION_MM = 0.0
MAX_PRECIPITATION_MM = 2000.0
MIN_HUMIDITY_PCT = 0.0
MAX_HUMIDITY_PCT = 100.0


def validate_temperature_range(value: float) -> list[str]:
    errors: list[str] = []
    if value < MIN_TEMPERATURE_C:
        errors.append(f"Temperature {value}°C is below minimum {MIN_TEMPERATURE_C}°C")
    elif value > MAX_TEMPERATURE_C:
        errors.append(f"Temperature {value}°C is above maximum {MAX_TEMPERATURE_C}°C")
    return errors


def validate_precipitation_range(value: float) -> list[str]:
    errors: list[str] = []
    if value < MIN_PRECIPITATION_MM:
        errors.append(f"Precipitation {value}mm is below minimum {MIN_PRECIPITATION_MM}mm")
    elif value > MAX_PRECIPITATION_MM:
        errors.append(f"Precipitation {value}mm is above maximum {MAX_PRECIPITATION_MM}mm")
    return errors


def validate_humidity_range(value: float) -> list[str]:
    errors: list[str] = []
    if value < MIN_HUMIDITY_PCT:
        errors.append(f"Humidity {value}% is below minimum {MIN_HUMIDITY_PCT}%")
    elif value > MAX_HUMIDITY_PCT:
        errors.append(f"Humidity {value}% is above maximum {MAX_HUMIDITY_PCT}%")
    return errors


def validate_timestamps(obs_list: list[WeatherObservation]) -> list[str]:
    errors: list[str] = []
    for i in range(1, len(obs_list)):
        if obs_list[i].timestamp < obs_list[i - 1].timestamp:
            errors.append(
                f"Timestamp out of order at index {i}: {obs_list[i].timestamp} < {obs_list[i - 1].timestamp}"
            )
    return errors


def detect_outliers(
    obs_list: list[WeatherObservation], method: str = "iqr"
) -> list[WeatherObservation]:
    if len(obs_list) < 4:
        return []
    if method == "iqr":
        return _detect_outliers_iqr(obs_list)
    else:
        raise ValueError(f"Unsupported outlier detection method: {method}")


def _detect_outliers_iqr(obs_list: list[WeatherObservation]) -> list[WeatherObservation]:
    temperatures = [o.temperature_2m for o in obs_list]
    sorted_temps = sorted(temperatures)
    n = len(sorted_temps)
    q1 = sorted_temps[n // 4]
    q3 = sorted_temps[3 * n // 4]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return [
        obs
        for obs in obs_list
        if obs.temperature_2m < lower_bound or obs.temperature_2m > upper_bound
    ]


def remove_duplicates(obs_list: list[WeatherObservation]) -> list[WeatherObservation]:
    seen: set[tuple[str, datetime]] = set()
    result: list[WeatherObservation] = []
    for obs in obs_list:
        key = (obs.location_id, obs.timestamp)
        if key not in seen:
            seen.add(key)
            result.append(obs)
    return result


def check_coverage(
    obs_list: list[WeatherObservation],
    start: datetime,
    end: datetime,
    expected_frequency: str = "hourly",
) -> float:
    if expected_frequency == "hourly":
        expected_count = int((end - start).total_seconds() // 3600) + 1
    else:
        expected_count = 1
    if expected_count == 0:
        return 0.0
    actual_count = len(obs_list)
    return min(actual_count / expected_count, 1.0)


@dataclass
class QualityReport:
    location_id: str
    total_observations: int
    passed_checks: int
    failed_checks: int
    errors: list[str]
    coverage_fraction: float
    outlier_count: int = 0
    duplicate_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        total = self.passed_checks + self.failed_checks
        if total == 0:
            return 1.0
        return self.passed_checks / total
