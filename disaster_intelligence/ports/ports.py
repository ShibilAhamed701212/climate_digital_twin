from __future__ import annotations

from typing import Any, Protocol

from disaster_intelligence.domain.entities import (
    Assessment,
    DisasterEvent,
    InferenceResult,
    Job,
    Scene,
    TwinOverlayPointer,
)


class StacPort(Protocol):
    def search(
        self,
        aoi: dict[str, Any],
        dt_start: str,
        dt_end: str | None,
        collections: list[str],
        max_cloud_pct: float | None = None,
    ) -> list[dict[str, Any]]: ...

    def download(self, href: str, dest_uri: str) -> str: ...


class RasterStore(Protocol):
    def put_bytes(self, name: str, data: bytes) -> str: ...

    def path_for(self, name: str) -> str: ...

    def exists(self, uri: str) -> bool: ...


class VectorStore(Protocol):
    def write_features(
        self, assessment_id: str, name: str, features: list[dict[str, Any]]
    ) -> str: ...

    def read_features(self, assessment_id: str, name: str) -> list[dict[str, Any]]: ...


class JobRepository(Protocol):
    def create(self, job: Job) -> Job: ...

    def get(self, job_id: str) -> Job | None: ...

    def get_by_idempotency(self, key: str) -> Job | None: ...

    def update(self, job: Job) -> Job: ...

    def list_inflight(self) -> list[Job]: ...


class EventRepository(Protocol):
    def create(self, event: DisasterEvent) -> DisasterEvent: ...

    def get(self, event_id: str) -> DisasterEvent | None: ...

    def list_events(
        self, limit: int, offset: int, disaster_type: str | None = None
    ) -> tuple[list[DisasterEvent], int]: ...


class SceneRepository(Protocol):
    def upsert(self, scene: Scene) -> Scene: ...

    def get(self, scene_id: str) -> Scene | None: ...

    def list_for_event(self, event_id: str) -> list[Scene]: ...


class AssessmentRepository(Protocol):
    def put(self, assessment: Assessment) -> Assessment: ...

    def get(self, assessment_id: str) -> Assessment | None: ...

    def list_for_event(self, event_id: str) -> list[Assessment]: ...

    def latest_for_location(self, location_id: str) -> Assessment | None: ...

    def index_location(self, location_id: str, assessment_id: str) -> None: ...


class ModelRunner(Protocol):
    def run(self, task: str, mask_or_path: Any, **kwargs: Any) -> InferenceResult: ...


class OsmPort(Protocol):
    def load(self, aoi: dict[str, Any]) -> dict[str, list[dict[str, Any]]]: ...


class TwinPointerPort(Protocol):
    def upsert(self, pointer: TwinOverlayPointer) -> None: ...
