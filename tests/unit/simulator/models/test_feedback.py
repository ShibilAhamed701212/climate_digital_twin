from datetime import UTC, datetime

import pytest

from simulator.models.feedback import FeedbackRecord, ModelCorrection, PredictionError


class TestPredictionError:
    def test_create(self):
        pe = PredictionError(
            entity_id="ent-1",
            prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
            prediction={"temp": 30.0, "humid": 50.0},
            observation={"temp": 29.5, "humid": 52.0},
            errors={"temp": 0.5, "humid": -2.0},
            absolute_errors={"temp": 0.5, "humid": 2.0},
            squared_errors={"temp": 0.25, "humid": 4.0},
        )
        assert pe.entity_id == "ent-1"
        assert pe.errors == {"temp": 0.5, "humid": -2.0}
        assert len(pe.error_id) == 16

    def test_defaults(self):
        pe = PredictionError(
            entity_id="ent-1",
            prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
            prediction={"temp": 30.0},
            observation={"temp": 29.5},
            errors={"temp": 0.5},
            absolute_errors={"temp": 0.5},
            squared_errors={"temp": 0.25},
        )
        assert pe.model_name == "unknown"
        assert pe.model_version == "0.0.0"
        assert pe.forecast_horizon is None
        assert pe.metadata == {}

    def test_key_mismatch_raises(self):
        with pytest.raises(ValueError, match="Variable keys mismatch"):
            PredictionError(
                entity_id="ent-1",
                prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
                observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
                prediction={"temp": 30.0},
                observation={"temp": 29.5},
                errors={"temp": 0.5},
                absolute_errors={"temp": 0.5, "extra": 1.0},
                squared_errors={"temp": 0.25},
            )

    def test_forecast_horizon_and_metadata(self):
        pe = PredictionError(
            entity_id="ent-1",
            prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
            prediction={"temp": 30.0},
            observation={"temp": 29.5},
            errors={"temp": 0.5},
            absolute_errors={"temp": 0.5},
            squared_errors={"temp": 0.25},
            model_name="gfs",
            model_version="1.0.0",
            forecast_horizon=24,
            metadata={"source": "test"},
        )
        assert pe.forecast_horizon == 24
        assert pe.metadata["source"] == "test"


class TestModelCorrection:
    def test_create(self):
        mc = ModelCorrection(
            model_name="gfs",
            model_version="1.0.0",
            correction_type="bias_adjustment",
            description="Corrected temperature bias",
            parameters_before={"bias": 2.0},
            parameters_after={"bias": 0.5},
            metrics_before={"mae": 3.0},
            metrics_after={"mae": 1.5},
        )
        assert mc.model_name == "gfs"
        assert mc.trigger == "manual"
        assert mc.verification_status == "pending"
        assert len(mc.correction_id) == 16

    def test_optional_fields(self):
        mc = ModelCorrection(
            model_name="gfs",
            model_version="1.0.0",
            correction_type="bias_adjustment",
            description="Corrected temperature bias",
            parameters_before={},
            parameters_after={},
            metrics_before={},
            metrics_after={},
            trigger="drift_detected",
            applied_by="admin",
            verification_status="verified",
        )
        assert mc.trigger == "drift_detected"
        assert mc.applied_by == "admin"
        assert mc.verification_status == "verified"


class TestFeedbackRecord:
    def test_create(self):
        pe = PredictionError(
            entity_id="ent-1",
            prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
            prediction={"temp": 30.0},
            observation={"temp": 29.5},
            errors={"temp": 0.5},
            absolute_errors={"temp": 0.5},
            squared_errors={"temp": 0.25},
        )
        fr = FeedbackRecord(
            entity_id="ent-1",
            cycle_start=datetime(2024, 6, 15, 12, tzinfo=UTC),
            prediction_errors=[pe],
            num_samples=10,
        )
        assert fr.entity_id == "ent-1"
        assert fr.status == "open"
        assert len(fr.prediction_errors) == 1
        assert fr.drift_detected is False
        assert len(fr.record_id) == 16

    def test_negative_num_samples_raises(self):
        with pytest.raises(ValueError, match="Number of samples must be non-negative"):
            FeedbackRecord(
                entity_id="ent-1",
                cycle_start=datetime(2024, 6, 15, 12, tzinfo=UTC),
                prediction_errors=[],
                num_samples=-1,
            )

    def test_zero_samples_accepted(self):
        fr = FeedbackRecord(
            entity_id="ent-1",
            cycle_start=datetime(2024, 6, 15, 12, tzinfo=UTC),
            prediction_errors=[],
            num_samples=0,
        )
        assert fr.num_samples == 0

    def test_complete_cycle(self):
        pe = PredictionError(
            entity_id="ent-1",
            prediction_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
            observation_timestamp=datetime(2024, 6, 15, 13, tzinfo=UTC),
            prediction={"temp": 30.0},
            observation={"temp": 29.5},
            errors={"temp": 0.5},
            absolute_errors={"temp": 0.5},
            squared_errors={"temp": 0.25},
        )
        mc = ModelCorrection(
            model_name="gfs",
            model_version="1.0.0",
            correction_type="bias_adjustment",
            description="Fix",
            parameters_before={},
            parameters_after={},
            metrics_before={},
            metrics_after={},
        )
        fr = FeedbackRecord(
            entity_id="ent-1",
            cycle_start=datetime(2024, 6, 15, 12, tzinfo=UTC),
            prediction_errors=[pe],
            drift_detected=True,
            num_samples=5,
            status="closed",
            cycle_end=datetime(2024, 6, 15, 14, tzinfo=UTC),
            correction=mc,
            correction_successful=True,
            drift_metrics={"drift_score": 0.7},
            notes="Cycle completed",
        )
        assert fr.status == "closed"
        assert fr.correction_successful is True
        assert fr.drift_metrics == {"drift_score": 0.7}
