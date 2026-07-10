from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pipeline.sources.dataset_registry import DatasetRegistry

_logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    max_concurrent_jobs: int = 3
    default_horizon_days: int = 16
    incremental_backfill_days: int = 30
    retry_failed_jobs: bool = True
    max_retries: int = 3


@dataclass
class ScheduledJob:
    source_name: str
    location_id: str
    job_type: str
    start_date: date
    end_date: date
    horizon_days: int = 16
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retry_count: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:16])


class IngestionScheduler:
    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()
        self.jobs: list[ScheduledJob] = []
        self._lock = __import__("threading").Lock()
        _logger.info("IngestionScheduler initialized")

    def add_job(
        self,
        source_name: str,
        location_id: str,
        job_type: str,
        start_date: date,
        end_date: date,
        horizon_days: int = 16,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        job = ScheduledJob(
            source_name=source_name,
            location_id=location_id,
            job_type=job_type,
            start_date=start_date,
            end_date=end_date,
            horizon_days=horizon_days,
            metadata=metadata or {},
        )
        with self._lock:
            self.jobs.append(job)
        return job

    def get_job(self, job_id: str) -> ScheduledJob | None:
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        return None

    def get_jobs_by_status(self, status: str) -> list[ScheduledJob]:
        return [job for job in self.jobs if job.status == status]

    def update_job_status(self, job_id: str, status: str, error_message: str | None = None) -> None:
        with self._lock:
            job = self.get_job(job_id)
            if job is not None:
                job.status = status
                if error_message is not None:
                    job.error_message = error_message
                if status == "failed":
                    job.retry_count += 1

    def detect_gaps(
        self,
        location_id: str,
        source_name: str,
        start_date: date,
        end_date: date,
        registry: DatasetRegistry,
    ) -> list[tuple[date, date]]:
        gaps: list[tuple[date, date]] = []
        current_gap_start: date | None = None
        current = start_date
        while current <= end_date:
            status = registry.get_ingestion_status(source_name, current)
            if status is None:
                if current_gap_start is None:
                    current_gap_start = current
            else:
                if current_gap_start is not None:
                    gaps.append((current_gap_start, current - timedelta(days=1)))
                    current_gap_start = None
            current += timedelta(days=1)
        if current_gap_start is not None:
            gaps.append((current_gap_start, end_date))
        if gaps:
            _logger.info("Detected %d gap(s) for %s / %s", len(gaps), source_name, location_id)
        return gaps

    def list_locations_due(self) -> list[str]:
        location_ids = sorted({job.location_id for job in self.jobs if job.status == "pending"})
        return location_ids

    def clear_completed(self) -> None:
        with self._lock:
            self.jobs = [job for job in self.jobs if job.status not in ("completed", "failed")]

    @property
    def pending_count(self) -> int:
        return len(self.get_jobs_by_status("pending"))

    @property
    def running_count(self) -> int:
        return len(self.get_jobs_by_status("running"))

    @property
    def completed_count(self) -> int:
        return len(self.get_jobs_by_status("completed"))

    @property
    def failed_count(self) -> int:
        return len(self.get_jobs_by_status("failed"))
