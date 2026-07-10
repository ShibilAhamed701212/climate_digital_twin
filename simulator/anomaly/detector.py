from __future__ import annotations

import logging

import numpy as np

from simulator.historical.computer import BaselineComputer, _get_obs_value
from simulator.models.baseline import (
    AnomalyCategory,
    AnomalyReport,
    AnomalyResult,
    BaselineRecord,
)
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)

ANOMALY_THRESHOLDS = {
    "temperature_2m": {"extreme_high": 3.0, "high": 2.0, "low": -2.0, "extreme_low": -3.0},
    "precipitation_mm": {"extreme_high": 3.0, "high": 2.0, "low": -1.5, "extreme_low": -2.5},
    "humidity_pct": {"extreme_high": 3.0, "high": 2.0, "low": -2.0, "extreme_low": -3.0},
    "pressure_hpa": {"extreme_high": 3.0, "high": 2.0, "low": -2.0, "extreme_low": -3.0},
    "wind_speed_10m": {"extreme_high": 3.0, "high": 2.0, "low": -1.5, "extreme_low": -2.5},
}

VARIABLE_NAMES = {
    "temperature_2m": "Temperature at 2m",
    "precipitation_mm": "Precipitation",
    "humidity_pct": "Relative Humidity",
    "pressure_hpa": "Atmospheric Pressure",
    "wind_speed_10m": "Wind Speed at 10m",
    "wind_direction_10m": "Wind Direction",
    "solar_radiation": "Solar Radiation",
    "cloud_cover_pct": "Cloud Cover",
    "soil_moisture": "Soil Moisture",
}


class AnomalyDetector:
    def __init__(self, baseline_computer: BaselineComputer | None = None) -> None:
        self._baseline_computer = baseline_computer or BaselineComputer()

    def classify_anomaly(self, z_score: float, variable: str) -> AnomalyCategory:
        thresholds = ANOMALY_THRESHOLDS.get(variable, ANOMALY_THRESHOLDS["temperature_2m"])
        if z_score >= thresholds["extreme_high"]:
            return AnomalyCategory.EXTREME_HIGH
        if z_score >= thresholds["high"]:
            return AnomalyCategory.HIGH
        if z_score <= thresholds["extreme_low"]:
            return AnomalyCategory.EXTREME_LOW
        if z_score <= thresholds["low"]:
            return AnomalyCategory.LOW
        return AnomalyCategory.NORMAL

    def compute_anomaly_score(self, z_score: float) -> float:
        return float(1.0 / (1.0 + np.exp(-abs(z_score) + 2.0)))

    def detect_anomaly(
        self,
        observation: WeatherObservation,
        baseline: BaselineRecord,
        variable: str,
    ) -> AnomalyResult:
        current = _get_obs_value(observation, variable)
        if current is None:
            return AnomalyResult(
                location_id=observation.location_id,
                variable=variable,
                timestamp=observation.timestamp,
                current_value=0.0,
                baseline_mean=baseline.mean,
                baseline_std=baseline.std,
                z_score=0.0,
                anomaly_score=0.0,
                category=AnomalyCategory.NORMAL,
                is_significant=False,
            )

        z_score = (current - baseline.mean) / baseline.std if baseline.std > 0 else 0.0

        category = self.classify_anomaly(z_score, variable)
        anomaly_score = self.compute_anomaly_score(z_score)
        is_significant = category in (
            AnomalyCategory.EXTREME_HIGH,
            AnomalyCategory.EXTREME_LOW,
        )

        return AnomalyResult(
            location_id=observation.location_id,
            variable=variable,
            timestamp=observation.timestamp,
            current_value=current,
            baseline_mean=baseline.mean,
            baseline_std=baseline.std,
            z_score=z_score,
            anomaly_score=anomaly_score,
            category=category,
            is_significant=is_significant,
        )

    def detect_anomalies(
        self,
        observation: WeatherObservation,
        variables: list[str] | None = None,
    ) -> AnomalyReport:
        if variables is None:
            variables = list(VARIABLE_NAMES.keys())

        report = AnomalyReport(
            location_id=observation.location_id,
            timestamp=observation.timestamp,
        )

        for variable in variables:
            baseline = self._baseline_computer.get_baseline_for_date(
                location_id=observation.location_id,
                variable=variable,
                target_date=observation.timestamp.date(),
            )
            if baseline is None:
                continue

            result = self.detect_anomaly(observation, baseline, variable)
            report.anomalies.append(result)

        category_counts: dict[str, int] = {}
        for a in report.anomalies:
            cat = a.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        report.summary = category_counts

        return report

    def detect_batch_anomalies(
        self,
        observations: list[WeatherObservation],
        variables: list[str] | None = None,
    ) -> list[AnomalyReport]:
        return [self.detect_anomalies(obs, variables) for obs in observations]

    def get_anomaly_trend(
        self,
        location_id: str,
        observations: list[WeatherObservation],
        variable: str,
    ) -> list[AnomalyResult]:
        results: list[AnomalyResult] = []
        for obs in sorted(observations, key=lambda o: o.timestamp):
            baseline = self._baseline_computer.get_baseline_for_date(
                location_id=location_id,
                variable=variable,
                target_date=obs.timestamp.date(),
            )
            if baseline is None:
                continue
            results.append(self.detect_anomaly(obs, baseline, variable))
        return results

    def compute_spi(
        self,
        precipitation_values: np.ndarray,
    ) -> float:
        non_zero = precipitation_values[precipitation_values > 0]
        if len(non_zero) < 10:
            return 0.0

        import scipy.stats as stats

        gamma_fitted = stats.gamma.fit(non_zero, floc=0)
        p_zero = float(np.sum(precipitation_values == 0)) / len(precipitation_values)

        prob = stats.gamma.cdf(0.5, *gamma_fitted)
        prob = p_zero + (1 - p_zero) * prob
        prob = np.clip(prob, 1e-10, 1 - 1e-10)

        spi = float(stats.norm.ppf(prob))
        return spi

    def compute_drought_severity(self, spi: float) -> str:
        if spi <= -2.0:
            return "extreme_drought"
        if spi <= -1.5:
            return "severe_drought"
        if spi <= -1.0:
            return "moderate_drought"
        if spi <= -0.5:
            return "abnormally_dry"
        return "normal"
