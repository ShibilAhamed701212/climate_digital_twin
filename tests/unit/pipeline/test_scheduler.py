"""Tests for pipeline.scheduler with 100% coverage."""

from __future__ import annotations

import sys
from datetime import date, datetime
from unittest.mock import MagicMock

# Prevent circular import caused by pipeline.sources.__init__ importing
# from pipeline.scheduler before its own module-level imports complete.
mock_registry_module = MagicMock()
mock_registry_module.DatasetRegistry = MagicMock()
sys.modules["pipeline.sources.dataset_registry"] = mock_registry_module

from pipeline.scheduler import IngestionScheduler, SchedulerConfig


class FakeRegistry:
    def __init__(self, status_map: dict[tuple[str, date], str | None]) -> None:
        self._status = status_map

    def get_ingestion_status(self, source: str, dt: date) -> str | None:
        return self._status.get((source, dt))


class TestSchedulerConfig:
    def test_default_config(self) -> None:
        cfg = SchedulerConfig()
        assert cfg.max_concurrent_jobs == 3
        assert cfg.default_horizon_days == 16
        assert cfg.incremental_backfill_days == 30
        assert cfg.retry_failed_jobs is True
        assert cfg.max_retries == 3

    def test_custom_config(self) -> None:
        cfg = SchedulerConfig(max_concurrent_jobs=5, max_retries=1)
        assert cfg.max_concurrent_jobs == 5
        assert cfg.max_retries == 1


class TestIngestionSchedulerInit:
    def test_default_config(self) -> None:
        sched = IngestionScheduler()
        assert isinstance(sched.config, SchedulerConfig)
        assert sched.config.max_concurrent_jobs == 3
        assert sched.jobs == []

    def test_custom_config(self) -> None:
        cfg = SchedulerConfig(max_concurrent_jobs=10)
        sched = IngestionScheduler(config=cfg)
        assert sched.config.max_concurrent_jobs == 10


class TestAddJob:
    def test_adds_job_with_defaults(self) -> None:
        sched = IngestionScheduler()
        job = sched.add_job("source1", "loc1", "forecast", date(2024, 1, 1), date(2024, 1, 5))
        assert job.source_name == "source1"
        assert job.location_id == "loc1"
        assert job.job_type == "forecast"
        assert job.start_date == date(2024, 1, 1)
        assert job.end_date == date(2024, 1, 5)
        assert job.horizon_days == 16
        assert job.status == "pending"
        assert job.metadata == {}
        assert len(job.job_id) == 16
        assert job.retry_count == 0
        assert job.error_message is None
        assert isinstance(job.created_at, datetime)
        assert job in sched.jobs

    def test_adds_job_with_metadata(self) -> None:
        sched = IngestionScheduler()
        meta = {"priority": "high"}
        job = sched.add_job(
            "s2",
            "loc2",
            "backfill",
            date(2024, 2, 1),
            date(2024, 2, 3),
            horizon_days=7,
            metadata=meta,
        )
        assert job.metadata == {"priority": "high"}
        assert job.horizon_days == 7


class TestGetJob:
    def test_found(self) -> None:
        sched = IngestionScheduler()
        job = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        assert sched.get_job(job.job_id) is job

    def test_not_found(self) -> None:
        sched = IngestionScheduler()
        assert sched.get_job("nonexistent") is None


class TestGetJobsByStatus:
    def test_filters_by_status(self) -> None:
        sched = IngestionScheduler()
        j1 = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        j2 = sched.add_job("s", "l", "t", date(2024, 1, 3), date(2024, 1, 4))
        sched.update_job_status(j1.job_id, "running")
        assert sched.get_jobs_by_status("pending") == [j2]
        assert sched.get_jobs_by_status("running") == [j1]
        assert sched.get_jobs_by_status("completed") == []


class TestUpdateJobStatus:
    def test_updates_status_and_error(self) -> None:
        sched = IngestionScheduler()
        job = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        sched.update_job_status(job.job_id, "running")
        assert job.status == "running"
        sched.update_job_status(job.job_id, "failed", error_message="timeout")
        assert job.status == "failed"
        assert job.error_message == "timeout"

    def test_failed_increments_retry_count(self) -> None:
        sched = IngestionScheduler()
        job = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        assert job.retry_count == 0
        sched.update_job_status(job.job_id, "failed")
        assert job.retry_count == 1
        sched.update_job_status(job.job_id, "failed")
        assert job.retry_count == 2

    def test_non_existent_job_does_nothing(self) -> None:
        sched = IngestionScheduler()
        sched.update_job_status("nope", "running")
        assert sched.jobs == []


class TestDetectGaps:
    def _make_registry(self, statuses: dict[tuple[str, str], str | None]) -> FakeRegistry:
        return FakeRegistry({(s, date.fromisoformat(d)): v for (s, d), v in statuses.items()})

    def test_no_gaps(self) -> None:
        reg = self._make_registry(
            {("src", "2024-01-01"): "ok", ("src", "2024-01-02"): "ok", ("src", "2024-01-03"): "ok"}
        )
        sched = IngestionScheduler()
        gaps = sched.detect_gaps("loc", "src", date(2024, 1, 1), date(2024, 1, 3), reg)
        assert gaps == []

    def test_gap_at_start(self) -> None:
        reg = self._make_registry({("src", "2024-01-03"): "ok", ("src", "2024-01-04"): "ok"})
        sched = IngestionScheduler()
        gaps = sched.detect_gaps("loc", "src", date(2024, 1, 1), date(2024, 1, 4), reg)
        assert gaps == [(date(2024, 1, 1), date(2024, 1, 2))]

    def test_gap_at_middle(self) -> None:
        reg = self._make_registry(
            {("src", "2024-01-01"): "ok", ("src", "2024-01-02"): "ok", ("src", "2024-01-05"): "ok"}
        )
        sched = IngestionScheduler()
        gaps = sched.detect_gaps("loc", "src", date(2024, 1, 1), date(2024, 1, 5), reg)
        assert gaps == [(date(2024, 1, 3), date(2024, 1, 4))]

    def test_gap_at_end(self) -> None:
        reg = self._make_registry({("src", "2024-01-01"): "ok", ("src", "2024-01-02"): "ok"})
        sched = IngestionScheduler()
        gaps = sched.detect_gaps("loc", "src", date(2024, 1, 1), date(2024, 1, 5), reg)
        assert gaps == [(date(2024, 1, 3), date(2024, 1, 5))]

    def test_multiple_gaps(self) -> None:
        reg = self._make_registry({("src", "2024-01-02"): "ok", ("src", "2024-01-04"): "ok"})
        sched = IngestionScheduler()
        gaps = sched.detect_gaps("loc", "src", date(2024, 1, 1), date(2024, 1, 5), reg)
        assert gaps == [
            (date(2024, 1, 1), date(2024, 1, 1)),
            (date(2024, 1, 3), date(2024, 1, 3)),
            (date(2024, 1, 5), date(2024, 1, 5)),
        ]


class TestListLocationsDue:
    def test_returns_sorted_unique_pending_locations(self) -> None:
        sched = IngestionScheduler()
        sched.add_job("s", "z-loc", "t", date(2024, 1, 1), date(2024, 1, 2))
        sched.add_job("s", "a-loc", "t", date(2024, 1, 1), date(2024, 1, 2))
        sched.add_job("s", "a-loc", "t", date(2024, 1, 3), date(2024, 1, 4))
        assert sched.list_locations_due() == ["a-loc", "z-loc"]

    def test_excludes_non_pending(self) -> None:
        sched = IngestionScheduler()
        j = sched.add_job("s", "loc", "t", date(2024, 1, 1), date(2024, 1, 2))
        sched.update_job_status(j.job_id, "running")
        assert sched.list_locations_due() == []


class TestClearCompleted:
    def test_removes_completed_and_failed_keeps_others(self) -> None:
        sched = IngestionScheduler()
        p = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        r = sched.add_job("s", "l", "t", date(2024, 1, 2), date(2024, 1, 3))
        c = sched.add_job("s", "l", "t", date(2024, 1, 3), date(2024, 1, 4))
        f = sched.add_job("s", "l", "t", date(2024, 1, 4), date(2024, 1, 5))
        sched.update_job_status(r.job_id, "running")
        sched.update_job_status(c.job_id, "completed")
        sched.update_job_status(f.job_id, "failed")
        sched.clear_completed()
        assert sched.jobs == [p, r]


class TestCountProperties:
    def test_counts(self) -> None:
        sched = IngestionScheduler()
        j1 = sched.add_job("s", "l", "t", date(2024, 1, 1), date(2024, 1, 2))
        j2 = sched.add_job("s", "l", "t", date(2024, 1, 2), date(2024, 1, 3))
        j3 = sched.add_job("s", "l", "t", date(2024, 1, 3), date(2024, 1, 4))
        sched.add_job("s", "l", "t", date(2024, 1, 4), date(2024, 1, 5))
        sched.update_job_status(j1.job_id, "running")
        sched.update_job_status(j2.job_id, "completed")
        sched.update_job_status(j3.job_id, "failed")
        assert sched.pending_count == 1
        assert sched.running_count == 1
        assert sched.completed_count == 1
        assert sched.failed_count == 1
