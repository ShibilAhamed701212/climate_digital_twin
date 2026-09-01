from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventCreateRequest(BaseModel):
    disaster_type: str
    aoi: dict[str, Any]
    t_start: str
    name: str = ""
    location_ids: list[str] = Field(default_factory=list)
    t_end: str | None = None


class StacIngestRequest(BaseModel):
    event_id: str
    collections: list[str] = Field(default_factory=lambda: ["sentinel-1-grd", "sentinel-2-l2a"])
    datetime: str
    max_cloud_pct: float | None = 20.0


class JobCreateRequest(BaseModel):
    event_id: str
    tasks: list[str] = Field(default_factory=list)
    pair: dict[str, Any] = Field(default_factory=lambda: {"mode": "auto"})
    twin_sync: bool = True


class DropIngestRequest(BaseModel):
    event_id: str
    license: str = "user-drop"


class ReliefPlanRequest(BaseModel):
    assessment_id: str
