"""Phase 7 — SimulationService.

Orchestrates the coupled simulation: load REAL forcing → run deterministic
engine → persist to SimulationStore (dedicated, isolated).  Outputs carry
``authenticity = SIMULATED`` and are never written to ObservationStore /
ForecastStore / HazardStore / AlertStore.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from climatedt.simulation.engine import CoupledSimulationEngine
from climatedt.simulation.forcing import load_bengaluru_forcing, load_grid_forcing
from climatedt.simulation.models import (
    SimulationRun,
    build_provenance,
    compute_run_id,
    new_run_id,
)
from climatedt.simulation.parameters import SimulationParameters
from climatedt.simulation.store import SimulationStore

logger = logging.getLogger(__name__)

BENGALURU_LOCATION_ID = "bengaluru"


class SimulationService:
    def __init__(
        self,
        engine: CoupledSimulationEngine | None = None,
        store: SimulationStore | None = None,
    ) -> None:
        self._engine = engine or CoupledSimulationEngine()
        self._store = store or SimulationStore()

    # ── runs ─────────────────────────────────────────────────────────────

    def run_bengaluru(self, parameters: SimulationParameters | None = None) -> SimulationRun:
        """Run the coupled simulation over the full Bengaluru REAL record."""
        forcing, source = load_bengaluru_forcing()
        return self._run(forcing, source, BENGALURU_LOCATION_ID, parameters)

    def run_grid(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameters: SimulationParameters | None = None,
    ) -> SimulationRun:
        """Run the coupled simulation over a NASA POWER grid-cell window."""
        forcing, source = load_grid_forcing(latitude, longitude, start_date, end_date)
        location_id = f"grid-{latitude}-{longitude}"
        return self._run(forcing, source, location_id, parameters)

    def _run(
        self,
        forcing: list[Any],
        source: Any,
        location_id: str,
        parameters: SimulationParameters | None,
    ) -> SimulationRun:
        started = time.perf_counter()
        run = self._engine.run(
            forcing,
            location_id=location_id,
            forcing_source=source,
            parameters=parameters,
        )
        run.run_id = compute_run_id(
            location_id, run.steps[0].date, run.steps[-1].date, run.config_version
        )
        run.provenance = build_provenance(
            location_id=location_id,
            forcing=source,
            parameters=run.parameters,
            parameter_sources=run.parameter_sources,
            initial_condition_mm=run.initial_condition_mm,
            equations=run.provenance.get("equations", []),
        )
        self._store.save_run(run)
        logger.info(
            "Simulation run %s for %s (%d days) in %.1f ms",
            run.run_id,
            location_id,
            len(run.steps),
            (time.perf_counter() - started) * 1000.0,
        )
        return run

    # ── store access ─────────────────────────────────────────────────────

    def get_run(self, run_id: str) -> SimulationRun | None:
        return self._store.get_run(run_id)

    def list_runs(
        self, location_id: str | None = None, limit: int | None = None
    ) -> list[SimulationRun]:
        return self._store.list_runs(location_id, limit)
