"""Phase 7 — Simulation models and provenance.

Every simulation artifact carries ``authenticity = SIMULATED`` (never REAL).
Provenance records the full chain: forcing source → model equations/versions
→ parameters/sources → initial condition → run identity.  This module is
deliberately self-contained (no imports from the rest of the codebase) so it
can never accidentally inherit REAL semantics.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from climatedt.simulation.parameters import (
    CONFIG_VERSION,
    METHOD,
    METHOD_VERSION,
    SIMULATED_AUTHENTICITY,
)

SPINUP_DAYS = 90  # documented physical warm-up before results are reported


@dataclass(frozen=True)
class ForcingSource:
    """Where the REAL driving data came from (never fabricated)."""

    name: str
    path: str
    rows: int
    start_date: str
    end_date: str
    variables: tuple[str, ...]
    authenticity: str = "REAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "rows": self.rows,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "variables": list(self.variables),
            "authenticity": self.authenticity,
        }


@dataclass(frozen=True)
class DailyForcing:
    """A single day of REAL forcing."""

    date: str
    tmax_c: float
    tmin_c: float
    rainfall_mm: float
    humidity_pct: float | None = None
    wind_speed_ms: float | None = None
    solar_radiation_mj: float | None = None
    pressure_kpa: float | None = None


@dataclass
class SimulationStep:
    """One simulated day of the coupled land-surface state."""

    date: str
    pet_mm: float
    aet_mm: float
    runoff_mm: float
    drainage_mm: float
    storage_start_mm: float
    storage_mm: float
    dryness: float
    soil_moisture_m3m3: float  # deprecated — use relative_soil_water
    relative_soil_water: float  # storage / capacity (dimensionless proxy)
    precipitation_mm: float
    et_method: str = "HARGREAVES_SAMANI"

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "pet_mm": self.pet_mm,
            "aet_mm": self.aet_mm,
            "runoff_mm": self.runoff_mm,
            "drainage_mm": self.drainage_mm,
            "storage_start_mm": self.storage_start_mm,
            "storage_mm": self.storage_mm,
            "dryness": self.dryness,
            "soil_moisture_m3m3": self.soil_moisture_m3m3,
            "relative_soil_water": self.relative_soil_water,
            "precipitation_mm": self.precipitation_mm,
            "et_method": self.et_method,
        }


def _mass_balance_residual(step: SimulationStep, prior_storage: float) -> float:
    """Residual = S(t+1) - S(t) - P + AET + Runoff + Drainage (should be ~0)."""
    return (
        step.storage_mm
        - prior_storage
        - step.precipitation_mm
        + step.aet_mm
        + step.runoff_mm
        + step.drainage_mm
    )


@dataclass
class SimulationRun:
    """A complete, deterministic coupled simulation run."""

    run_id: str
    location_id: str
    forcing: ForcingSource
    parameters: dict[str, Any]
    parameter_sources: dict[str, str]
    initial_condition_mm: float
    spinup_days: int
    steps: list[SimulationStep]
    provenance: dict[str, Any]
    authenticity: str = SIMULATED_AUTHENTICITY
    method: str = METHOD
    method_version: str = METHOD_VERSION
    config_version: str = CONFIG_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # ── summary statistics ───────────────────────────────────────────────

    @property
    def totals(self) -> dict[str, float]:
        return {
            "precipitation_mm": round(sum(s.precipitation_mm for s in self.steps), 2),
            "pet_mm": round(sum(s.pet_mm for s in self.steps), 2),
            "aet_mm": round(sum(s.aet_mm for s in self.steps), 2),
            "runoff_mm": round(sum(s.runoff_mm for s in self.steps), 2),
            "drainage_mm": round(sum(s.drainage_mm for s in self.steps), 2),
        }

    @property
    def extremes(self) -> dict[str, dict[str, str | float]]:
        return {
            "max_runoff_day": {
                "date": str(max(self.steps, key=lambda s: s.runoff_mm).date),
                "runoff_mm": round(max(s.runoff_mm for s in self.steps), 2),
                "precipitation_mm": round(
                    max(self.steps, key=lambda s: s.runoff_mm).precipitation_mm, 2
                ),
            },
            "max_storage_day": {
                "date": str(max(self.steps, key=lambda s: s.storage_mm).date),
                "storage_mm": round(max(s.storage_mm for s in self.steps), 2),
            },
            "min_storage_day": {
                "date": str(min(self.steps, key=lambda s: s.storage_mm).date),
                "storage_mm": round(min(s.storage_mm for s in self.steps), 2),
            },
            "max_pet_day": {
                "date": str(max(self.steps, key=lambda s: s.pet_mm).date),
                "pet_mm": round(max(s.pet_mm for s in self.steps), 2),
            },
        }

    @property
    def mass_balance(self) -> dict[str, float]:
        """Cumulative mass balance over the run (residual ~= 0, from raw
        per-step values; any small non-zero is rounding noise, not a leak —
        the bucket equation is exact by construction)."""
        storage_in = self.steps[0].storage_start_mm if self.steps else 0.0
        storage_out = self.steps[-1].storage_mm if self.steps else 0.0
        precip = sum(s.precipitation_mm for s in self.steps)
        aet = sum(s.aet_mm for s in self.steps)
        runoff = sum(s.runoff_mm for s in self.steps)
        drainage = sum(s.drainage_mm for s in self.steps)
        residual = storage_out - storage_in - precip + aet + runoff + drainage
        return {
            "storage_change_mm": round(storage_out - storage_in, 4),
            "residual_mm": round(residual, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "location_id": self.location_id,
            "forcing": self.forcing.to_dict(),
            "parameters": dict(self.parameters),
            "parameter_sources": dict(self.parameter_sources),
            "initial_condition_mm": self.initial_condition_mm,
            "spinup_days": self.spinup_days,
            "steps": [s.to_dict() for s in self.steps],
            "provenance": self.provenance,
            "authenticity": self.authenticity,
            "method": self.method,
            "method_version": self.method_version,
            "config_version": self.config_version,
            "created_at": self.created_at,
            "totals": self.totals,
            "extremes": self.extremes,
            "mass_balance": self.mass_balance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationRun:
        forcing_data = data.get("forcing", {})
        steps = [
            SimulationStep(
                date=s["date"],
                pet_mm=s["pet_mm"],
                aet_mm=s["aet_mm"],
                runoff_mm=s["runoff_mm"],
                drainage_mm=s["drainage_mm"],
                storage_start_mm=s.get("storage_start_mm", s["storage_mm"]),
                storage_mm=s["storage_mm"],
                dryness=s["dryness"],
                soil_moisture_m3m3=s.get("soil_moisture_m3m3", 0.0),
                relative_soil_water=s.get("relative_soil_water", s.get("soil_moisture_m3m3", 0.0)),
                precipitation_mm=s["precipitation_mm"],
                et_method=s.get("et_method", "HARGREAVES_SAMANI"),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            run_id=data["run_id"],
            location_id=data["location_id"],
            forcing=ForcingSource(
                name=forcing_data.get("name", ""),
                path=forcing_data.get("path", ""),
                rows=forcing_data.get("rows", 0),
                start_date=forcing_data.get("start_date", ""),
                end_date=forcing_data.get("end_date", ""),
                variables=tuple(forcing_data.get("variables", [])),
                authenticity=forcing_data.get("authenticity", "REAL"),
            ),
            parameters=data.get("parameters", {}),
            parameter_sources=data.get("parameter_sources", {}),
            initial_condition_mm=data.get("initial_condition_mm", 0.0),
            spinup_days=data.get("spinup_days", 0),
            steps=steps,
            provenance=data.get("provenance", {}),
            authenticity=data.get("authenticity", SIMULATED_AUTHENTICITY),
            method=data.get("method", METHOD),
            method_version=data.get("method_version", METHOD_VERSION),
            config_version=data.get("config_version", CONFIG_VERSION),
            created_at=data.get("created_at", ""),
        )


def new_run_id() -> str:
    return f"sim_{uuid.uuid4().hex[:12]}"


def build_provenance(
    *,
    location_id: str,
    forcing: ForcingSource,
    parameters: dict[str, Any],
    parameter_sources: dict[str, str],
    initial_condition_mm: float,
    equations: list[dict[str, str]],
) -> dict[str, Any]:
    """Build the full provenance chain for a run."""
    return {
        "authenticity": SIMULATED_AUTHENTICITY,
        "location_id": location_id,
        "forcing": forcing.to_dict(),
        "equations": equations,
        "parameters": dict(parameters),
        "parameter_sources": dict(parameter_sources),
        "initial_condition_mm": initial_condition_mm,
        "method": METHOD,
        "method_version": METHOD_VERSION,
        "config_version": CONFIG_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "note": (
            "All state variables are model outputs (SIMULATED). Forcing is "
            "REAL observed data; model outputs are never written to "
            "ObservationStore/ForecastStore/HazardStore/AlertStore."
        ),
    }


def compute_run_id(location_id: str, start: str, end: str, config_version: str) -> str:
    payload = {
        "location_id": location_id,
        "start": start,
        "end": end,
        "config_version": config_version,
        "method_version": METHOD_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sim_{digest[:16]}"
