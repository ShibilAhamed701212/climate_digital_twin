from __future__ import annotations

from datetime import datetime

import pytest

from pipeline.sources.quality import (
    QualityReport,
    check_coverage,
    detect_outliers,
    remove_duplicates,
    validate_humidity_range,
    validate_precipitation_range,
    validate_temperature_range,
    validate_timestamps,
)
from simulator.models.weather import WeatherObservation


def _obs(
    temperature_2m: float = 25.0,
    precipitation_mm: float = 0.0,
    humidity_pct: float = 50.0,
    timestamp: datetime | None = None,
    location_id: str = "loc1",
) -> WeatherObservation:
    return WeatherObservation(
        location_id=location_id,
        latitude=15.0,
        longitude=75.0,
        timestamp=timestamp or datetime(2024, 1, 1, 0, 0),
        temperature_2m=temperature_2m,
        precipitation_mm=precipitation_mm,
        humidity_pct=humidity_pct,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=90.0,
    )


class TestValidateTemperatureRange:
    def test_below_min(self):
        assert validate_temperature_range(-51.0) == ["Temperature -51.0°C is below minimum -50.0°C"]

    def test_above_max(self):
        assert validate_temperature_range(61.0) == ["Temperature 61.0°C is above maximum 60.0°C"]

    def test_normal(self):
        assert validate_temperature_range(25.0) == []

    def test_at_min_boundary(self):
        assert validate_temperature_range(-50.0) == []

    def test_at_max_boundary(self):
        assert validate_temperature_range(60.0) == []


class TestValidatePrecipitationRange:
    def test_below_min(self):
        assert validate_precipitation_range(-0.1) == ["Precipitation -0.1mm is below minimum 0.0mm"]

    def test_above_max(self):
        assert validate_precipitation_range(2000.1) == [
            "Precipitation 2000.1mm is above maximum 2000.0mm"
        ]

    def test_normal(self):
        assert validate_precipitation_range(10.0) == []

    def test_at_zero(self):
        assert validate_precipitation_range(0.0) == []


class TestValidateHumidityRange:
    def test_below_min(self):
        assert validate_humidity_range(-0.1) == ["Humidity -0.1% is below minimum 0.0%"]

    def test_above_max(self):
        assert validate_humidity_range(100.1) == ["Humidity 100.1% is above maximum 100.0%"]

    def test_normal(self):
        assert validate_humidity_range(50.0) == []

    def test_at_boundaries(self):
        assert validate_humidity_range(0.0) == []
        assert validate_humidity_range(100.0) == []


class TestValidateTimestamps:
    def test_in_order(self):
        obs = [
            _obs(timestamp=datetime(2024, 1, 1, 0, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 2, 0)),
        ]
        assert validate_timestamps(obs) == []

    def test_out_of_order(self):
        obs = [
            _obs(timestamp=datetime(2024, 1, 1, 2, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 0, 0)),
        ]
        errors = validate_timestamps(obs)
        assert len(errors) == 2
        assert "Timestamp out of order at index 1" in errors[0]
        assert "Timestamp out of order at index 2" in errors[1]

    def test_empty_list(self):
        assert validate_timestamps([]) == []

    def test_single_item(self):
        assert validate_timestamps([_obs()]) == []

    def test_multiple_out_of_order(self):
        obs = [
            _obs(timestamp=datetime(2024, 1, 1, 3, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 2, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0)),
            _obs(timestamp=datetime(2024, 1, 1, 0, 0)),
        ]
        assert len(validate_timestamps(obs)) == 3


class TestDetectOutliers:
    def test_less_than_four_returns_empty(self):
        obs = [_obs(temperature_2m=25.0) for _ in range(3)]
        assert detect_outliers(obs) == []

    def test_iqr_no_outliers(self):
        obs = [_obs(temperature_2m=float(t)) for t in range(20, 30)]
        assert detect_outliers(obs, method="iqr") == []

    def test_iqr_with_outliers(self):
        obs = [
            _obs(temperature_2m=float(t)) for t in [10, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 50]
        ]
        outliers = detect_outliers(obs, method="iqr")
        assert len(outliers) == 2
        assert outliers[0].temperature_2m == 10.0
        assert outliers[1].temperature_2m == 50.0

    def test_unsupported_method_raises(self):
        obs = [_obs(temperature_2m=25.0) for _ in range(5)]
        with pytest.raises(ValueError, match="Unsupported outlier detection method: zscore"):
            detect_outliers(obs, method="zscore")


class TestRemoveDuplicates:
    def test_deduplicates_by_location_id_and_timestamp(self):
        ts = datetime(2024, 1, 1, 0, 0)
        obs = [
            _obs(timestamp=ts, location_id="a"),
            _obs(timestamp=ts, location_id="a"),
            _obs(timestamp=ts, location_id="b"),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0), location_id="a"),
        ]
        result = remove_duplicates(obs)
        assert len(result) == 3

    def test_no_duplicates(self):
        obs = [
            _obs(timestamp=datetime(2024, 1, 1, 0, 0), location_id="a"),
            _obs(timestamp=datetime(2024, 1, 1, 1, 0), location_id="a"),
        ]
        assert remove_duplicates(obs) == obs

    def test_empty_list(self):
        assert remove_duplicates([]) == []


class TestCheckCoverage:
    def test_hourly_frequency(self):
        obs = [_obs() for _ in range(5)]
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 4, 0)
        assert check_coverage(obs, start, end, "hourly") == 1.0

    def test_hourly_partial_coverage(self):
        obs = [_obs() for _ in range(3)]
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 5, 0)
        assert check_coverage(obs, start, end, "hourly") == 0.5

    def test_non_hourly_frequency(self):
        obs = [_obs() for _ in range(5)]
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 4, 0)
        assert check_coverage(obs, start, end, "daily") == 1.0

    def test_expected_count_zero(self):
        obs = [_obs() for _ in range(5)]
        start = datetime(2024, 1, 1, 0, 0, 1)
        end = datetime(2024, 1, 1, 0, 0)
        assert check_coverage(obs, start, end, "hourly") == 0.0

    def test_no_observations(self):
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 3, 0)
        cov = check_coverage([], start, end, "hourly")
        assert cov == 0.0


class TestQualityReport:
    def test_pass_rate_normal(self):
        r = QualityReport(
            "loc1", 10, passed_checks=8, failed_checks=2, errors=[], coverage_fraction=1.0
        )
        assert r.pass_rate == 0.8

    def test_pass_rate_all_passed(self):
        r = QualityReport(
            "loc1", 5, passed_checks=5, failed_checks=0, errors=[], coverage_fraction=1.0
        )
        assert r.pass_rate == 1.0

    def test_pass_rate_total_zero(self):
        r = QualityReport(
            "loc1", 0, passed_checks=0, failed_checks=0, errors=[], coverage_fraction=0.0
        )
        assert r.pass_rate == 1.0
