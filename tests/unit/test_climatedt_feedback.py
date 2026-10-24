"""Tests for climatedt.feedback storage, capture and analytics."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from climatedt.feedback import storage as storage_module
from climatedt.feedback.analysis import FeedbackAnalyzer
from climatedt.feedback.capture import CapturedFeedback, FeedbackCaptureService
from climatedt.feedback.storage import FeedbackStore, _record_to_dict


@pytest.fixture
def jsonl(tmp_path, monkeypatch):
    path = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(storage_module, "_FEEDBACK_DIR", tmp_path)
    monkeypatch.setattr(storage_module, "_JSONL_PATH", path)
    return path


class TestFeedbackStore:
    def test_persists_and_reloads_records(self, jsonl) -> None:
        store = FeedbackStore()
        store.save(CapturedFeedback(location_id="blr", rating=4, comment="good"))

        reloaded = FeedbackStore().list_all()

        assert len(reloaded) == 1
        assert reloaded[0].location_id == "blr"
        assert reloaded[0].rating == 4.0

    def test_skips_blank_and_bad_lines(self, jsonl) -> None:
        jsonl.write_text('\n{"rating": 3, "location_id": "a"}\nnot-json\n')

        records = FeedbackStore().list_all()

        assert [r.location_id for r in records] == ["a"]

    def test_non_persistent_store_writes_nothing(self, jsonl) -> None:
        store = FeedbackStore(persist=False)
        store.save(CapturedFeedback(rating=5))

        assert len(store.list_all()) == 1
        assert not jsonl.exists()

    def test_record_to_dict_fallbacks(self) -> None:
        assert _record_to_dict(SimpleNamespace(rating=2, _private=1)) == {"rating": 2}
        assert _record_to_dict(3) == {"rating": 0, "comment": ""}


class TestFeedbackCaptureService:
    @pytest.fixture
    def service(self) -> FeedbackCaptureService:
        return FeedbackCaptureService(store=FeedbackStore(persist=False))

    async def test_risk_feedback_records_corrected_score(self, service) -> None:
        rec = await service.capture_risk_feedback("a-1", 2, corrected_risk_score=0.4, comment="x")

        assert rec.feedback_type == "risk"
        assert rec.comment == "x corrected_score=0.4"
        assert service.store.list_all() == [rec]

    async def test_forecast_feedback_records_observed_values(self, service) -> None:
        rec = await service.capture_forecast_feedback("f-1", 5, observed_values={"rain": 1.0})

        assert rec.feedback_type == "forecast"
        assert rec.comment == "observed={'rain': 1.0}"

    async def test_general_feedback_defaults_type(self, service) -> None:
        rec = await service.capture_general_feedback("loc", "", 3, comment="ok")

        assert rec.feedback_type == "general"
        assert rec.to_dashboard_row()["location"] == "loc"

    def test_default_store_is_created(self, jsonl) -> None:
        assert isinstance(FeedbackCaptureService().store, FeedbackStore)


class TestFeedbackAnalyzer:
    def _analyzer(self, ratings: list[float], loc: str = "blr") -> FeedbackAnalyzer:
        store = FeedbackStore(persist=False)
        for i, r in enumerate(ratings):
            store.save(
                CapturedFeedback(
                    rating=r, location_id=loc, feedback_type="risk" if i % 2 else "forecast"
                )
            )
        return FeedbackAnalyzer(store)

    async def test_overview_stats(self) -> None:
        stats = await self._analyzer([2, 4, 4]).get_overview_stats()

        assert stats["total_feedback"] == 3
        assert stats["avg_rating"] == pytest.approx(10 / 3)
        assert stats["rating_counts"] == {"2": 1, "4": 2}
        assert stats["feedback_types"] == {"forecast": 2, "risk": 1}

    async def test_overview_stats_empty(self) -> None:
        stats = await self._analyzer([]).get_overview_stats()

        assert stats["total_feedback"] == 0 and stats["avg_rating"] == 0.0

    @pytest.mark.parametrize(
        ("ratings", "direction"),
        [([2, 2, 4, 4], "improving"), ([4, 4, 2, 2], "declining"), ([3, 3], "stable")],
    )
    async def test_improvement_trend(self, ratings, direction) -> None:
        trend = await self._analyzer(ratings).get_improvement_trend()

        assert trend["trend_direction"] == direction

    async def test_improvement_trend_needs_two_points(self) -> None:
        trend = await self._analyzer([5]).get_improvement_trend()

        assert trend["trend_direction"] == "insufficient_data"

    async def test_location_performance(self) -> None:
        analyzer = self._analyzer([1, 2, 3, 4, 5, 5])

        perf = await analyzer.get_location_performance("blr")
        missing = await analyzer.get_location_performance("nowhere")

        assert perf["total_feedback"] == 6
        assert perf["recent_avg"] == pytest.approx(3.8)
        assert missing["trend"] == "insufficient_data"

    def test_dashboard_rows_support_plain_records(self) -> None:
        store = SimpleNamespace(
            list_all=lambda: [CapturedFeedback(rating=4), SimpleNamespace(rating=2, comment="c")]
        )

        rows = FeedbackAnalyzer(store).list_dashboard_rows()

        assert rows[0]["rating"] == 4.0
        assert rows[1] == {
            "date": "",
            "location": "unknown",
            "rating": 2.0,
            "type": "general",
            "comment": "c",
            "record_id": "",
        }
