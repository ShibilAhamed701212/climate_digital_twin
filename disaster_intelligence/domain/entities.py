from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from disaster_intelligence.domain.enums import (
    Authenticity,
    DamageClass,
    DisasterType,
    JobStatus,
    LayerKind,
)
from disaster_intelligence.domain.ids import ulid


def _now() -> datetime:
    return datetime.now(UTC)


def utc_iso(value: datetime | None = None) -> str:
    dt = value or _now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


@dataclass
class GeoLayer:
    layer_id: str
    name: str
    kind: str
    uri: str
    media_type: str
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DisasterEvent:
    event_id: str
    disaster_type: str
    aoi: dict[str, Any]
    t_start: str
    status: str = "open"
    name: str = ""
    location_ids: list[str] = field(default_factory=list)
    t_end: str | None = None
    created_at: str = field(default_factory=utc_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        disaster_type: DisasterType | str,
        aoi: dict[str, Any],
        t_start: str,
        name: str = "",
        location_ids: list[str] | None = None,
        t_end: str | None = None,
    ) -> DisasterEvent:
        return cls(
            event_id=ulid(),
            disaster_type=str(disaster_type),
            aoi=aoi,
            t_start=t_start,
            name=name,
            location_ids=list(location_ids or []),
            t_end=t_end,
        )


@dataclass
class Scene:
    scene_id: str
    provider: str
    acquired_at: str
    license: str
    authenticity: str
    event_id: str | None = None
    platform: str | None = None
    product: str | None = None
    cloud_pct: float | None = None
    crs: str = "EPSG:4326"
    stac_href: str | None = None
    local_uri: str | None = None
    checksum_sha256: str | None = None
    bounds: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImagePair:
    pair_id: str
    event_id: str
    after_scene_id: str
    before_scene_id: str | None = None
    coreg_rmse_px: float | None = None
    policy_id: str = "nearest_pre_7d"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Job:
    job_id: str
    event_id: str
    status: str
    tasks: list[str]
    progress_pct: int = 0
    stage: str = "queued"
    idempotency_key: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    assessment_id: str | None = None
    twin_sync_ok: bool | None = None
    created_at: str = field(default_factory=utc_iso)
    updated_at: str = field(default_factory=utc_iso)
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(cls, event_id: str, tasks: list[str], idempotency_key: str | None = None) -> Job:
        return cls(
            job_id=ulid(),
            event_id=event_id,
            status=JobStatus.QUEUED.value,
            tasks=tasks,
            idempotency_key=idempotency_key,
        )


@dataclass
class Assessment:
    assessment_id: str
    event_id: str
    version: int
    job_id: str
    disaster_type: str
    model_cards: dict[str, str]
    layers: list[dict[str, Any]]
    kpis: dict[str, Any]
    quality_flags: list[str]
    authenticity: str
    confidence_mean: float | None = None
    parent_assessment_id: str | None = None
    twin_sync_ok: bool | None = None
    created_at: str = field(default_factory=utc_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TwinOverlayPointer:
    location_id: str
    assessment_id: str
    event_id: str
    disaster_type: str
    href_assessment: str
    updated_at: str
    source: str = "disaster-engine"
    kpis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReliefPlan:
    plan_id: str
    assessment_id: str
    zones: list[dict[str, Any]]
    method: str = "weighted_v0"
    created_at: str = field(default_factory=utc_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InferenceResult:
    task: str
    metrics: dict[str, Any]
    output_uris: list[str]
    duration_ms: float
    quality_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "GeoLayer",
    "DisasterEvent",
    "Scene",
    "ImagePair",
    "Job",
    "Assessment",
    "TwinOverlayPointer",
    "ReliefPlan",
    "InferenceResult",
    "utc_iso",
    "Authenticity",
    "DamageClass",
    "LayerKind",
]
