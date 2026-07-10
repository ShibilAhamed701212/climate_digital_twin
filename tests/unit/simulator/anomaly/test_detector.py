from datetime import UTC, datetime
from unittest.mock import patch

import numpy as np
import pytest

from simulator.anomaly.detector import (
    ANOMALY_THRESHOLDS,
    VARIABLE_NAMES,
    AnomalyDetector,
)
from simulator.models.baseline import AnomalyCategory, BaselineRecord, BaselineType
from simulator.models.weather import WeatherObservation


def make_obs(temp=25.0, loc="loc1"):
    return WeatherObservation(
        location_id=loc,
        latitude=10.0,
        longitude=20.0,
        timestamp=datetime(2024, 6, 15, tzinfo=UTC),
        temperature_2m=temp,
        precipitation_mm=0.0,
        humidity_pct=50.0,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=180.0,
    )


def make_baseline(mean=25.0, std=2.0):
    return BaselineRecord(
        location_id="loc1",
        variable="temperature_2m",
        baseline_type=BaselineType.DAILY,
        mean=mean,
        std=std,
    )


class TestConstants:
    def test_thresholds_defined(self):
        assert "temperature_2m" in ANOMALY_THRESHOLDS
        assert "precipitation_mm" in ANOMALY_THRESHOLDS

    def test_variable_names(self):
        assert "temperature_2m" in VARIABLE_NAMES
        assert VARIABLE_NAMES["temperature_2m"] == "Temperature at 2m"


class TestClassifyAnomaly:
    def test_normal(self):
        detector = AnomalyDetector()
        assert detector.classify_anomaly(0.0, "temperature_2m") == AnomalyCategory.NORMAL
        assert detector.classify_anomaly(1.0, "temperature_2m") == AnomalyCategory.NORMAL
        assert detector.classify_anomaly(-1.0, "temperature_2m") == AnomalyCategory.NORMAL

    def test_high(self):
        detector = AnomalyDetector()
        assert detector.classify_anomaly(2.5, "temperature_2m") == AnomalyCategory.HIGH

    def test_extreme_high(self):
        detector = AnomalyDetector()
        assert detector.classify_anomaly(3.5, "temperature_2m") == AnomalyCategory.EXTREME_HIGH
        assert detector.classify_anomaly(3.0, "temperature_2m") == AnomalyCategory.EXTREME_HIGH

    def test_low(self):
        detector = AnomalyDetector()
        assert detector.classify_anomaly(-2.5, "temperature_2m") == AnomalyCategory.LOW

    def test_extreme_low(self):
        detector = AnomalyDetector()
        assert detector.classify_anomaly(-3.5, "temperature_2m") == AnomalyCategory.EXTREME_LOW
        assert detector.classify_anomaly(-3.0, "temperature_2m") == AnomalyCategory.EXTREME_LOW

    def test_unknown_variable_uses_default(self):
        detector = AnomalyDetector()
        result = detector.classify_anomaly(3.5, "unknown_var")
        assert result == AnomalyCategory.EXTREME_HIGH


class TestAnomalyScore:
    def test_score_zero(self):
        detector = AnomalyDetector()
        score = detector.compute_anomaly_score(0.0)
        assert score == pytest.approx(0.1192, rel=0.01)

    def test_score_high(self):
        detector = AnomalyDetector()
        score = detector.compute_anomaly_score(5.0)
        assert score == pytest.approx(0.9526, rel=0.01)

    def test_score_negative(self):
        detector = AnomalyDetector()
        score = detector.compute_anomaly_score(-3.0)
        assert score == pytest.approx(0.7311, rel=0.01)


class TestDetectAnomaly:
    def test_normal_value(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=26.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        result = detector.detect_anomaly(obs, baseline, "temperature_2m")
        assert result.z_score == 0.5
        assert result.category == AnomalyCategory.NORMAL
        assert result.is_significant is False

    def test_high_value(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        result = detector.detect_anomaly(obs, baseline, "temperature_2m")
        assert result.category == AnomalyCategory.HIGH

    def test_extreme_value(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=35.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        result = detector.detect_anomaly(obs, baseline, "temperature_2m")
        assert result.category == AnomalyCategory.EXTREME_HIGH
        assert result.is_significant is True

    def test_zero_std(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=25.0)
        baseline = make_baseline(mean=25.0, std=0.0)
        result = detector.detect_anomaly(obs, baseline, "temperature_2m")
        assert result.z_score == 0.0
        assert result.category == AnomalyCategory.NORMAL

    def test_none_value(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=25.0)
        baseline = make_baseline(mean=25.0, std=2.0)

        result = detector.detect_anomaly(obs, baseline, "nonexistent_field")
        assert result.z_score == 0.0
        assert result.is_significant is False

    def test_sets_current_value(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        result = detector.detect_anomaly(obs, baseline, "temperature_2m")
        assert result.current_value == 30.0
        assert result.baseline_mean == 25.0
        assert result.baseline_std == 2.0


class TestDetectAnomalies:
    def test_basic(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        report = detector.detect_anomalies(obs, variables=["temperature_2m"])
        assert len(report.anomalies) == 0

    def test_all_variables(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        report = detector.detect_anomalies(obs)
        assert report.location_id == "loc1"

    def test_with_baseline(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        with patch.object(
            detector._baseline_computer, "get_baseline_for_date", return_value=baseline
        ):
            report = detector.detect_anomalies(obs, variables=["temperature_2m"])
            assert len(report.anomalies) == 1
            assert report.anomalies[0].category == AnomalyCategory.HIGH

    def test_summary_counts(self):
        detector = AnomalyDetector()
        obs = make_obs(temp=30.0)
        baseline = make_baseline(mean=25.0, std=2.0)
        with patch.object(
            detector._baseline_computer, "get_baseline_for_date", return_value=baseline
        ):
            report = detector.detect_anomalies(
                obs, variables=["temperature_2m", "precipitation_mm"]
            )
            assert report.summary is not None
            assert sum(report.summary.values()) == len(report.anomalies)


class TestDetectBatchAnomalies:
    def test_basic(self):
        detector = AnomalyDetector()
        obs_list = [make_obs(temp=30.0), make_obs(temp=35.0)]
        reports = detector.detect_batch_anomalies(obs_list)
        assert len(reports) == 2


class TestGetAnomalyTrend:
    def test_basic(self):
        detector = AnomalyDetector()
        obs_list = [make_obs(temp=30.0)]
        trend = detector.get_anomaly_trend("loc1", obs_list, "temperature_2m")
        assert isinstance(trend, list)

    def test_with_baseline(self):
        detector = AnomalyDetector()
        obs_list = [make_obs(temp=30.0)]
        baseline = make_baseline(mean=25.0, std=2.0)
        with patch.object(
            detector._baseline_computer, "get_baseline_for_date", return_value=baseline
        ):
            trend = detector.get_anomaly_trend("loc1", obs_list, "temperature_2m")
            assert len(trend) == 1
            assert trend[0].category == AnomalyCategory.HIGH


class TestSPI:
    def test_insufficient_data(self):
        detector = AnomalyDetector()
        arr = np.array([0.0, 0.0, 0.0])
        result = detector.compute_spi(arr)
        assert result == 0.0

    def test_sufficient_data(self):
        detector = AnomalyDetector()
        rng = np.random.default_rng(42)
        arr = np.abs(rng.normal(10, 5, 50))
        result = detector.compute_spi(arr)
        assert isinstance(result, float)


class TestDroughtSeverity:
    def test_extreme(self):
        detector = AnomalyDetector()
        assert detector.compute_drought_severity(-2.5) == "extreme_drought"
        assert detector.compute_drought_severity(-2.0) == "extreme_drought"

    def test_severe(self):
        detector = AnomalyDetector()
        assert detector.compute_drought_severity(-1.8) == "severe_drought"

    def test_moderate(self):
        detector = AnomalyDetector()
        assert detector.compute_drought_severity(-1.2) == "moderate_drought"

    def test_abnormally_dry(self):
        detector = AnomalyDetector()
        assert detector.compute_drought_severity(-0.7) == "abnormally_dry"

    def test_normal(self):
        detector = AnomalyDetector()
        assert detector.compute_drought_severity(0.0) == "normal"
        assert detector.compute_drought_severity(1.0) == "normal"
