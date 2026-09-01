"""Scenario Engine API — exposes scenario simulation via REST.

Endpoints:
  GET   /health                       — health check
  POST  /scenarios/create             — create a new scenario definition
  POST  /scenarios/simulate           — run a scenario simulation
  GET   /scenarios                    — list all available scenarios
  GET   /scenarios/{scenario_id}/compare  — compare run with baseline
  POST  /scenarios/validate           — validate scenario parameters
  DELETE/scenarios/{scenario_id}      — delete a custom scenario
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from simulator.engine.twin_engine import DigitalTwinEngine
from simulator.services.scenario_service import ScenarioService

logger = logging.getLogger(__name__)

_engine: DigitalTwinEngine | None = None
_service: ScenarioService | None = None


class CreateScenarioRequest(BaseModel):
    scenario_id: str | None = None
    name: str = ""
    description: str = ""
    scenario_type: str = Field(
        ..., description="temperature, rainfall, monsoon, extreme_event, or combined"
    )
    parameters: dict[str, Any] = Field(default_factory=dict)


class SimulateRequest(BaseModel):
    scenario_id: str = Field(..., description="ID of the scenario to simulate")
    location_ids: list[str] | None = Field(
        None, description="Specific locations to simulate (all if omitted)"
    )


class ValidateRequest(BaseModel):
    scenario_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioRunResponse(BaseModel):
    run_id: str
    scenario: dict[str, Any]
    results: list[dict[str, Any]]
    started_at: str
    completed_at: str
    total_duration_ms: float
    location_count: int
    status: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _engine, _service
    _engine = DigitalTwinEngine()
    _service = ScenarioService(_engine)
    logger.info("ScenarioService initialized")
    yield
    _engine = None
    _service = None


app = FastAPI(title="Scenario Engine API", version="2.1.0", lifespan=lifespan)


def _get_service() -> ScenarioService:
    if _service is None:
        raise RuntimeError("Service not initialized")
    return _service


@app.get("/health")
def health():
    return {"status": "healthy", "service": "scenario-engine", "version": "2.1.0"}


@app.post("/scenarios/create")
def create_scenario(req: CreateScenarioRequest) -> dict[str, Any]:
    svc = _get_service()
    scenario = svc.create_scenario(
        scenario_id=req.scenario_id,
        name=req.name,
        description=req.description,
        scenario_type=req.scenario_type,
        parameters=req.parameters,
    )
    return scenario.to_dict()


@app.post("/scenarios/simulate", response_model=ScenarioRunResponse)
def simulate_scenario(req: SimulateRequest) -> dict[str, Any]:
    svc = _get_service()
    try:
        run = svc.run_simulation(req.scenario_id, req.location_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return run.to_dict()


@app.get("/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    svc = _get_service()
    return svc.list_scenarios()


@app.get("/scenarios/{scenario_id}/compare")
def compare_with_baseline(scenario_id: str) -> list[dict[str, Any]]:
    svc = _get_service()
    try:
        run = svc.run_simulation(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return svc.compare_with_baseline(run)


@app.post("/scenarios/validate")
def validate_scenario(req: ValidateRequest) -> dict[str, Any]:
    svc = _get_service()
    errors = svc.validate_scenario(req.scenario_type, req.parameters)
    return {"valid": len(errors) == 0, "errors": errors}


@app.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str) -> dict[str, Any]:
    svc = _get_service()
    deleted = svc.delete_scenario(scenario_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
    return {"deleted": True, "scenario_id": scenario_id}
