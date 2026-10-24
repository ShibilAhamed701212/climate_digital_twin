"""Tests for climatedt.feedback.online_learning.OnlineLearner."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from climatedt.feedback.online_learning import OnlineLearner


def _notes(*notes: str) -> list[SimpleNamespace]:
    return [SimpleNamespace(notes=n) for n in notes]


class TestPartialFit:
    async def test_without_registry_returns_false(self) -> None:
        assert await OnlineLearner().partial_fit_model("m", np.zeros((1, 1)), np.zeros(1)) is False

    @pytest.mark.parametrize("entry", [None, {"model": None}])
    async def test_missing_model_returns_false(self, entry) -> None:
        registry = SimpleNamespace(get=lambda _mid: entry)

        assert await OnlineLearner(registry).partial_fit_model("m", [[1]], [1]) is False

    async def test_uses_partial_fit_when_available(self) -> None:
        calls = []
        model = SimpleNamespace(partial_fit=lambda x, y: calls.append((x, y)))
        registry = SimpleNamespace(get=lambda _mid: {"model": model})

        assert await OnlineLearner(registry).partial_fit_model("m", [[1]], [2]) is True
        assert calls == [([[1]], [2])]

    async def test_warm_start_models_are_refit(self) -> None:
        calls = []
        model = SimpleNamespace(warm_start=False, fit=lambda x, y: calls.append(x))
        registry = SimpleNamespace(get=lambda _mid: model)

        assert await OnlineLearner(registry).partial_fit_model("m", [[1]], [2]) is True
        assert model.warm_start is True and calls == [[[1]]]

    async def test_unsupported_or_failing_models_return_false(self) -> None:
        plain = SimpleNamespace(get=lambda _mid: object())

        def _boom(_mid):
            raise RuntimeError("registry down")

        assert await OnlineLearner(plain).partial_fit_model("m", [[1]], [2]) is False
        failing = SimpleNamespace(get=_boom)
        assert await OnlineLearner(failing).partial_fit_model("m", [[1]], [2]) is False


class TestRiskThresholds:
    DEFAULT = {"moderate_threshold": 30.0, "high_threshold": 50.0, "extreme_threshold": 75.0}

    async def test_too_little_feedback_keeps_defaults(self) -> None:
        learner = OnlineLearner()

        assert await learner.update_risk_thresholds("blr", _notes("rating=1")) == self.DEFAULT

    async def test_low_ratings_lower_thresholds(self) -> None:
        records = _notes(*["rating=1 corrected=60.5"] * 21)

        result = await OnlineLearner().update_risk_thresholds("blr", records)

        assert result == {
            "moderate_threshold": 25.0,
            "high_threshold": 45.0,
            "extreme_threshold": 70.0,
        }

    async def test_high_ratings_raise_thresholds(self) -> None:
        result = await OnlineLearner().update_risk_thresholds("blr", _notes(*["rating=5"] * 21))

        assert result == {
            "moderate_threshold": 35.0,
            "high_threshold": 55.0,
            "extreme_threshold": 80.0,
        }


class TestRetrainSignals:
    def test_should_retrain(self) -> None:
        learner = OnlineLearner()

        assert learner.should_retrain("m", []) is False
        assert learner.should_retrain("m", [0.1, 0.12]) is False
        assert learner.should_retrain("m", [0.3, 0.2]) is True

    def test_compute_drift(self) -> None:
        learner = OnlineLearner()
        same = np.array([1.0, 2.0, 3.0, 4.0])

        assert learner.compute_drift(np.array([1.0]), same) == 0.0
        assert learner.compute_drift(same, same) == 0.0
        assert learner.compute_drift(same, same + 10) == 1.0

    def test_retrain_queue_lifecycle(self) -> None:
        learner = OnlineLearner()
        learner._signal_retrain("lstm")
        learner._signal_retrain("lstm")
        learner._signal_retrain("xgboost")

        assert {k: len(v) for k, v in learner.get_retrain_queue().items()} == {
            "lstm": 2,
            "xgboost": 1,
        }
        learner.clear_retrain_queue("lstm")
        assert list(learner.get_retrain_queue()) == ["xgboost"]
        learner.clear_retrain_queue()
        assert learner.get_retrain_queue() == {}

    async def test_incorporate_feedback_without_errors(self) -> None:
        feedback = SimpleNamespace(record_id="r1", prediction_errors=[])

        result = await OnlineLearner().incorporate_feedback(feedback)

        assert result["incorporated"] is True
        assert result["retrain_needed"] is False

    @staticmethod
    def _feedback(record_id: str, errors: list[float]) -> SimpleNamespace:
        pe = SimpleNamespace(
            model_name="xgb", absolute_errors={f"v{i}": e for i, e in enumerate(errors)}
        )
        return SimpleNamespace(record_id=record_id, prediction_errors=[pe])

    async def test_drift_compares_against_earlier_feedback(self) -> None:
        learner = OnlineLearner()

        first = await learner.incorporate_feedback(self._feedback("r1", [1.0, 1.1, 0.9, 1.05]))
        same = await learner.incorporate_feedback(self._feedback("r2", [1.0, 1.1, 0.9, 1.05]))
        shifted = await learner.incorporate_feedback(self._feedback("r3", [9.0, 9.5, 10.0, 8.7]))

        # No history yet, then an identical distribution: no drift.
        assert first["retrain_needed"] is False
        assert same["retrain_needed"] is False
        # Errors far outside the earlier distribution are flagged as drift.
        assert shifted["retrain_needed"] is True
        assert "xgb" in learner._retrain_queue

    def test_note_parsers(self) -> None:
        assert OnlineLearner._extract_rating_from_notes("x rating=4") == 4
        assert OnlineLearner._extract_rating_from_notes("none") is None
        assert OnlineLearner._extract_corrected_score("corrected=42.5") == 42.5
        assert OnlineLearner._extract_corrected_score("corrected=1.2.3") is None
        assert OnlineLearner._extract_corrected_score("none") is None
