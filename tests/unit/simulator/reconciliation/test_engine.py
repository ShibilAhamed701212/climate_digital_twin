"""Unit tests for simulator/reconciliation/engine.py."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from simulator.models.feedback import PredictionError
from simulator.models.weather import DataSource, QualityFlag, WeatherObservation


@pytest.fixture
def sample_observation():
    return WeatherObservation(
        location_id="KA-BLR-001",
        latitude=12.97,
        longitude=77.59,
        timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        temperature_2m=28.5,
        precipitation_mm=10.0,
        humidity_pct=65.0,
        pressure_hpa=1012.0,
        wind_speed_10m=3.5,
        wind_direction_10m=180.0,
        solar_radiation=500.0,
        cloud_cover_pct=40.0,
        soil_moisture=0.25,
        data_source=DataSource.OPEN_METEO,
        quality_flag=QualityFlag.VALIDATED,
    )


class TestReconciliationResult:
    def test_default_result_id_generated(self):
        from simulator.models.twin_state import TwinState
        from simulator.reconciliation.engine import ReconciliationResult

        state = TwinState(
            entity_id="e1",
            timestamp=datetime.now(UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
        )
        result = ReconciliationResult(
            entity_id="e1",
            original_state=state,
            reconciled_state=state,
        )
        assert len(result.result_id) == 16

    def test_result_id_provided(self):
        from simulator.models.twin_state import TwinState
        from simulator.reconciliation.engine import ReconciliationResult

        state = TwinState(
            entity_id="e1",
            timestamp=datetime.now(UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
        )
        result = ReconciliationResult(
            entity_id="e1",
            original_state=state,
            reconciled_state=state,
            result_id="custom_id_123",
        )
        assert result.result_id == "custom_id_123"


class TestStateReconcilerInit:
    def test_default_max_correction(self):
        from simulator.reconciliation.engine import StateReconciler

        r = StateReconciler()
        assert r._max_correction == 50.0

    def test_custom_max_correction(self):
        from simulator.reconciliation.engine import StateReconciler

        r = StateReconciler(max_correction_magnitude=10.0)
        assert r._max_correction == 10.0


class TestReconcile:
    @pytest.mark.asyncio
    async def test_reconcile_success(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        result = await reconciler.reconcile("KA-BLR-001", sample_observation)

        assert result.entity_id == "KA-BLR-001"
        assert result.success is True
        assert result.source == "open_meteo"
        assert result.prediction_error is not None
        assert result.correction_delta is not None

    @pytest.mark.asyncio
    async def test_reconcile_success_message(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        result = await reconciler.reconcile("KA-BLR-001", sample_observation)
        assert "Reconciled with" in result.message
        assert "open_meteo" in result.message


class TestComputePredictionError:
    @pytest.mark.asyncio
    async def test_compute_prediction_error(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        error = await reconciler.compute_prediction_error("KA-BLR-001", sample_observation)
        assert isinstance(error, PredictionError)
        assert error.entity_id == "KA-BLR-001"
        assert "temperature_2m" in error.errors
        assert "precipitation_mm" in error.errors

    @pytest.mark.asyncio
    async def test_errors_match_observation(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        error = await reconciler.compute_prediction_error("KA-BLR-001", sample_observation)
        for var in ["temperature_2m", "precipitation_mm", "humidity_pct"]:
            assert var in error.prediction
            assert var in error.observation


class TestGenerateCorrection:
    def test_correction_applied(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        predicted = reconciler._observation_to_state("KA-BLR-001", sample_observation)
        delta, corrected = reconciler._generate_correction(predicted, sample_observation)

        assert delta.entity_id == "KA-BLR-001"
        assert corrected.temperature_2m == sample_observation.temperature_2m
        assert corrected.precipitation_mm == sample_observation.precipitation_mm

    def test_correction_capped(self, sample_observation):
        from simulator.models.twin_state import TwinState
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler(max_correction_magnitude=1.0)
        obs = sample_observation
        predicted = TwinState(
            entity_id="KA-BLR-001",
            timestamp=obs.timestamp,
            temperature_2m=0.0,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
        )
        delta, corrected = reconciler._generate_correction(predicted, obs)

        assert abs(delta.delta_temperature) <= 1.0
        assert corrected.temperature_2m == 1.0

    def test_optional_fields_none(self, sample_observation):
        from simulator.models.twin_state import TwinState
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        obs = sample_observation
        predicted = TwinState(
            entity_id="KA-BLR-001",
            timestamp=obs.timestamp,
            temperature_2m=25.0,
            precipitation_mm=5.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
        )
        obs_no_optional = WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=obs.timestamp,
            temperature_2m=28.0,
            precipitation_mm=8.0,
            humidity_pct=55.0,
            pressure_hpa=1012.0,
            wind_speed_10m=3.0,
            wind_direction_10m=180.0,
        )
        delta, corrected = reconciler._generate_correction(predicted, obs_no_optional)
        assert corrected.solar_radiation is None
        assert corrected.cloud_cover_pct is None
        assert corrected.soil_moisture is None

    def test_optional_fields_present(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        predicted = reconciler._observation_to_state("KA-BLR-001", sample_observation)
        delta, corrected = reconciler._generate_correction(predicted, sample_observation)

        assert corrected.solar_radiation is not None
        assert corrected.cloud_cover_pct is not None
        assert corrected.soil_moisture is not None


class TestObservationToState:
    def test_converts_fields(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        state = reconciler._observation_to_state("KA-BLR-001", sample_observation)

        assert state.entity_id == "KA-BLR-001"
        assert state.temperature_2m == sample_observation.temperature_2m
        assert state.precipitation_mm == sample_observation.precipitation_mm
        assert state.humidity_pct == sample_observation.humidity_pct
        assert state.pressure_hpa == sample_observation.pressure_hpa
        assert state.wind_speed_10m == sample_observation.wind_speed_10m
        assert state.wind_direction_10m == sample_observation.wind_direction_10m
        assert state.solar_radiation == sample_observation.solar_radiation
        assert state.cloud_cover_pct == sample_observation.cloud_cover_pct
        assert state.soil_moisture == sample_observation.soil_moisture
        assert state.data_source == "open_meteo"
        assert state.quality_flag == "validated"


class TestComputeError:
    def test_compute_error_metrics(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        predicted = reconciler._observation_to_state("KA-BLR-001", sample_observation)
        error = reconciler._compute_error(predicted, sample_observation)

        assert isinstance(error, PredictionError)
        for var in ["temperature_2m", "precipitation_mm", "humidity_pct"]:
            assert var in error.errors
            assert var in error.absolute_errors
            assert var in error.squared_errors

    def test_optional_compute_error(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        predicted = reconciler._observation_to_state("KA-BLR-001", sample_observation)
        error = reconciler._compute_error(predicted, sample_observation)

        assert "solar_radiation" in error.errors
        assert "cloud_cover_pct" in error.errors


class TestComputeMAE:
    def test_compute_mae(self, sample_observation):
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        predicted = reconciler._observation_to_state("KA-BLR-001", sample_observation)
        error = reconciler._compute_error(predicted, sample_observation)
        mae = reconciler._compute_mae(error)

        assert mae >= 0.0

    def test_mae_empty_returns_zero(self):
        from simulator.models.feedback import PredictionError
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()
        error = PredictionError(
            entity_id="e1",
            prediction_timestamp=datetime.now(UTC),
            observation_timestamp=datetime.now(UTC),
            prediction={},
            observation={},
            errors={},
            absolute_errors={},
            squared_errors={},
        )
        assert reconciler._compute_mae(error) == 0.0


class TestReconcileFailure:
    @pytest.mark.asyncio
    async def test_reconcile_exception_returns_failure(self):
        import unittest.mock as mock

        from simulator.models.weather import WeatherObservation
        from simulator.reconciliation.engine import StateReconciler

        reconciler = StateReconciler()

        bad_obs = WeatherObservation(
            location_id="bad",
            latitude=12.0,
            longitude=77.0,
            timestamp=datetime.now(UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=2.0,
            wind_direction_10m=90.0,
        )
        with mock.patch.object(reconciler, "_generate_correction", side_effect=ValueError("boom")):
            result = await reconciler.reconcile("bad", bad_obs)

        assert result.success is False
        assert "Reconciliation failed" in result.message
        assert "boom" in result.message
