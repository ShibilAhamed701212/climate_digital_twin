from __future__ import annotations

from pathlib import Path
from typing import Any

from disaster_intelligence.adapters.storage.jsonl_store import JsonlStore
from disaster_intelligence.domain.entities import (
    Assessment,
    DisasterEvent,
    Job,
    Scene,
    utc_iso,
)


def _event(row: dict[str, Any]) -> DisasterEvent:
    return DisasterEvent(**{k: row[k] for k in DisasterEvent.__dataclass_fields__ if k in row})


def _job(row: dict[str, Any]) -> Job:
    return Job(**{k: row[k] for k in Job.__dataclass_fields__ if k in row})


def _scene(row: dict[str, Any]) -> Scene:
    return Scene(**{k: row[k] for k in Scene.__dataclass_fields__ if k in row})


def _assessment(row: dict[str, Any]) -> Assessment:
    return Assessment(**{k: row[k] for k in Assessment.__dataclass_fields__ if k in row})


class JsonlEventRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonlStore(path)

    def create(self, event: DisasterEvent) -> DisasterEvent:
        self._store.put(event.event_id, event.to_dict())
        return event

    def get(self, event_id: str) -> DisasterEvent | None:
        row = self._store.get(event_id)
        return _event(row) if row else None

    def list_events(
        self, limit: int, offset: int, disaster_type: str | None = None
    ) -> tuple[list[DisasterEvent], int]:
        rows = self._store.values()
        if disaster_type:
            rows = [r for r in rows if r.get("disaster_type") == disaster_type]
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(rows)
        sliced = rows[offset : offset + limit]
        return [_event(r) for r in sliced], total


class JsonlJobRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonlStore(path)

    def create(self, job: Job) -> Job:
        self._store.put(job.job_id, job.to_dict())
        return job

    def get(self, job_id: str) -> Job | None:
        row = self._store.get(job_id)
        return _job(row) if row else None

    def get_by_idempotency(self, key: str) -> Job | None:
        row = self._store.find(lambda r: r.get("idempotency_key") == key)
        return _job(row) if row else None

    def update(self, job: Job) -> Job:
        job.updated_at = utc_iso()
        self._store.put(job.job_id, job.to_dict())
        return job

    def list_inflight(self) -> list[Job]:
        return [_job(r) for r in self._store.values() if r.get("status") in {"queued", "running"}]

    def list_jobs(
        self,
        event_id: str | None,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Job], int]:
        rows = self._store.values()
        if event_id:
            rows = [r for r in rows if r.get("event_id") == event_id]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        rows.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or "", reverse=True)
        total = len(rows)
        sliced = rows[offset : offset + limit]
        return [_job(r) for r in sliced], total


class JsonlSceneRepository:
    def __init__(self, path: Path) -> None:
        self._store = JsonlStore(path)

    def upsert(self, scene: Scene) -> Scene:
        self._store.put(scene.scene_id, scene.to_dict())
        return scene

    def get(self, scene_id: str) -> Scene | None:
        row = self._store.get(scene_id)
        return _scene(row) if row else None

    def list_for_event(self, event_id: str) -> list[Scene]:
        return [_scene(r) for r in self._store.values() if r.get("event_id") == event_id]


class JsonlAssessmentRepository:
    def __init__(self, path: Path, location_index: Path) -> None:
        self._store = JsonlStore(path)
        self._index = JsonlStore(location_index)

    def put(self, assessment: Assessment) -> Assessment:
        self._store.put(assessment.assessment_id, assessment.to_dict())
        return assessment

    def get(self, assessment_id: str) -> Assessment | None:
        row = self._store.get(assessment_id)
        return _assessment(row) if row else None

    def list_for_event(self, event_id: str) -> list[Assessment]:
        rows = [r for r in self._store.values() if r.get("event_id") == event_id]
        rows.sort(key=lambda r: int(r.get("version") or 0), reverse=True)
        return [_assessment(r) for r in rows]

    def index_location(self, location_id: str, assessment_id: str) -> None:
        self._index.put(location_id, {"location_id": location_id, "assessment_id": assessment_id})

    def latest_for_location(self, location_id: str) -> Assessment | None:
        row = self._index.get(location_id)
        if not row:
            return None
        return self.get(str(row["assessment_id"]))
