"""Twin State Manager API — exposes DigitalTwinEngine via REST.

Endpoints:
  GET  /health                  — health check
  GET  /state/current           — get current state for a location
  GET  /state/history           — get historical states for a location
  POST /state/sync              — ingest a new observation into the twin
  GET  /forecast/state          — get forecast state for a location
  POST /scenarios/simulate      — apply a what-if scenario
  POST /rollback                — rollback twin to a specific version
  GET  /state/version-history   — get version history for a location
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from simulator.engine.twin_engine import DigitalTwinEngine
from simulator.entities.climate_entity import ClimateEntity

logger = logging.getLogger(__name__)

_engine: DigitalTwinEngine | None = None


# ── Pydantic Models ──────────────────────────────────────────────


class StateRequest(BaseModel):
    location_id: str = Field(..., description="Unique location identifier")


class StateResponse(BaseModel):
    location_id: str
    timestamp: str
    rainfall: float
    max_temp: float
    min_temp: float
    risk_score: float
    prediction_confidence: float
    scenario_id: str
    data_source: str
    state_type: str


class HistoryRequest(BaseModel):
    location_id: str = Field(..., description="Unique location identifier")
    time_range: str | None = Field(None, description="Optional time range filter")


class SyncRequest(BaseModel):
    location_id: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    district: str = ""
    timestamp: str | None = None
    rainfall: float = 0.0
    max_temp: float = 25.0
    min_temp: float = 18.0
    risk_score: float = 0.0
    prediction_confidence: float = 0.0
    data_source: str = "IMD"


class SyncResponse(BaseModel):
    version_id: int
    location_id: str


class ScenarioRequest(BaseModel):
    location_id: str
    scenario_id: str = Field(..., description="Scenario identifier")
    rainfall_delta: float = 0.0
    max_temp_delta: float = 0.0
    min_temp_delta: float = 0.0


class RollbackRequest(BaseModel):
    location_id: str
    version_id: int = Field(..., gt=0, description="Target version to rollback to")


class RollbackResponse(BaseModel):
    version_id: int
    location_id: str


class VersionHistoryItem(BaseModel):
    version_id: int
    timestamp: str
    state_type: str


# ── Lifespan ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _engine
    _engine = DigitalTwinEngine()
    logger.info("DigitalTwinEngine initialized")
    yield
    _engine = None


app = FastAPI(title="Twin State Manager API", version="1.0.0", lifespan=lifespan)


def _get_engine() -> DigitalTwinEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


# ── Health ───────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "healthy", "service": "twin-state-mgr", "version": "1.0.0"}


# ── State Endpoints ──────────────────────────────────────────────


@app.get("/state/current", response_model=StateResponse)
def get_current_state(location_id: str) -> dict[str, Any]:
    engine = _get_engine()
    state = engine.get_current_state(location_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No current state found for location '{location_id}'",
        )
    return StateResponse(**state).model_dump()


@app.get("/state/history", response_model=list[StateResponse])
def get_historical_state(location_id: str, time_range: str | None = None) -> list[dict[str, Any]]:
    engine = _get_engine()
    states = engine.get_historical_state(location_id, time_range)
    return [StateResponse(**s).model_dump() for s in states]


@app.get("/state/version-history", response_model=list[VersionHistoryItem])
def get_version_history(location_id: str) -> list[dict[str, Any]]:
    engine = _get_engine()
    return engine.get_state_history(location_id)


@app.post("/state/sync", response_model=SyncResponse, status_code=201)
def sync_observation(req: SyncRequest) -> dict[str, Any]:
    engine = _get_engine()
    entity = ClimateEntity(
        location_id=req.location_id,
        latitude=req.latitude,
        longitude=req.longitude,
        district=req.district,
        timestamp=req.timestamp or __import__("datetime").datetime.now().isoformat(),
        rainfall=req.rainfall,
        max_temp=req.max_temp,
        min_temp=req.min_temp,
        risk_score=req.risk_score,
        prediction_confidence=req.prediction_confidence,
        data_source=req.data_source,
    )
    try:
        result = engine.ingest_observation(entity)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return SyncResponse(**result).model_dump()


# ── Forecast ─────────────────────────────────────────────────────


@app.get("/forecast/state", response_model=StateResponse)
def get_forecast_state(location_id: str, horizon: str | None = None) -> dict[str, Any]:
    engine = _get_engine()
    state = engine.get_forecast_state(location_id, horizon)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast state found for location '{location_id}'",
        )
    return StateResponse(**state).model_dump()


# ── Scenarios ────────────────────────────────────────────────────


@app.post("/scenarios/simulate", response_model=SyncResponse, status_code=201)
def simulate_scenario(req: ScenarioRequest) -> dict[str, Any]:
    engine = _get_engine()
    current = engine.get_current_state(req.location_id)
    if current is None:
        raise HTTPException(
            status_code=404,
            detail=f"No current state found for location '{req.location_id}'",
        )
    entity = ClimateEntity.deserialize(current)
    modified = entity.update_state(
        rainfall=entity.rainfall + req.rainfall_delta,
        max_temp=entity.max_temp + req.max_temp_delta,
        min_temp=entity.min_temp + req.min_temp_delta,
    )
    try:
        result = engine.apply_scenario(modified, req.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return SyncResponse(**result).model_dump()


# ── Rollback ─────────────────────────────────────────────────────


@app.post("/rollback", response_model=RollbackResponse)
def rollback_state(req: RollbackRequest) -> dict[str, Any]:
    engine = _get_engine()
    try:
        result = engine.rollback(req.location_id, req.version_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return RollbackResponse(**result).model_dump()
