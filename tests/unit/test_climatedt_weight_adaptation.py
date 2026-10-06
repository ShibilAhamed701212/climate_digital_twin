"""Tests for climatedt.feedback.adaptation.WeightAdaptation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from climatedt.feedback.adaptation import WeightAdaptation


def _rec(notes: str, days_ago: int = 0) -> SimpleNamespace:
    return SimpleNamespace(notes=notes, cycle_start=datetime.now(UTC) - timedelta(days=days_ago))


class _Store:
    def __init__(self, records: list | None = None, fail: bool = False) -> None:
        self._records = records or []
        self._fail = fail

    async def query_feedback(self, location_id: str, limit: int) -> list:
        if self._fail:
            raise RuntimeError("store down")
        return self._records


DEFAULTS = {"lstm": 0.25, "xgboost": 0.25, "prophet": 0.25, "ensemble": 0.25}


class TestUpdateEnsembleWeights:
    async def test_defaults_without_store_or_location(self) -> None:
        assert await WeightAdaptation().update_ensemble_weights() == DEFAULTS
        assert await WeightAdaptation(feedback_store=_Store()).update_ensemble_weights() == DEFAULTS

    async def test_defaults_when_store_fails(self) -> None:
        wa = WeightAdaptation(feedback_store=_Store(fail=True))

        assert await wa.update_ensemble_weights(location_id="blr") == DEFAULTS
        assert await wa.get_current_weights(location_id="blr") == DEFAULTS

    async def test_weights_follow_ratings(self) -> None:
        store = _Store([_rec("model=lstm rating=5"), _rec("model=xgboost rating=2")])
        wa = WeightAdaptation(feedback_store=store)

        weights = await wa.update_ensemble_weights(location_id="blr")

        assert weights == pytest.approx({"lstm": 0.8, "xgboost": 0.2})
        assert await wa.get_current_weights(location_id="blr") == pytest.approx(weights)

    async def test_seasonal_adjustment_keeps_normalised(self) -> None:
        store = _Store([_rec("model=lstm rating=3"), _rec("model=prophet rating=3")])
        wa = WeightAdaptation(feedback_store=store)

        weights = await wa.update_ensemble_weights(location_id="blr", season="Summer")

        assert sum(weights.values()) == pytest.approx(1.0)
        assert weights["lstm"] > weights["prophet"]


class TestScoring:
    def test_recency_weighting_prefers_recent_feedback(self) -> None:
        scores = WeightAdaptation().compute_performance_score(
            [_rec("model=lstm rating=5", days_ago=0), _rec("model=lstm rating=1", days_ago=60)]
        )

        # Recent 5-star (weight 1.0) outweighs the 60-day-old 1-star (weight 0.25).
        assert scores["lstm"] == pytest.approx(1.0 / 1.25)

    def test_model_inferred_from_text_and_unrated_ignored(self) -> None:
        scores = WeightAdaptation().compute_performance_score(
            [_rec("Prophet forecast was great rating=5"), _rec("model=lstm no rating")]
        )

        assert scores == {"prophet": 1.0}

    def test_no_usable_records_returns_defaults(self) -> None:
        assert WeightAdaptation().compute_performance_score([_rec("nothing here")]) == DEFAULTS

    @pytest.mark.parametrize(
        ("days", "half_life", "expected"),
        [(0, 30, 1.0), (30, 30, 0.5), (-1, 30, 0.0), (10, 0, 1.0)],
    )
    def test_exponential_decay(self, days, half_life, expected) -> None:
        assert WeightAdaptation.exponential_decay_weight(days, half_life) == expected

    def test_normalize_zero_scores_is_uniform(self) -> None:
        assert WeightAdaptation._normalize_weights({"a": 0.0, "b": 0.0}) == {"a": 0.5, "b": 0.5}

    def test_unknown_season_is_noop(self) -> None:
        w = {"lstm": 0.6, "xgboost": 0.4}

        assert WeightAdaptation._apply_seasonal_adjustment(w, "monsoon") is w
