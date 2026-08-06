"""Phase 7 — SimulationStore.

JSONL persistence under ``data/simulations/``.  Never writes to
ObservationStore / ForecastStore / the Twin repository / HazardStore /
AlertStore.  Loads existing files on init (restart recovery); saves are
idempotent on ``run_id``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from climatedt.simulation.models import SimulationRun
from climatedt.simulation.parameters import SIMULATED_AUTHENTICITY

logger = logging.getLogger(__name__)

DEFAULT_BASE_DIR = "data/simulations"


class SimulationStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        base = base_dir or os.environ.get("CLIMATEDT_SIMULATION_DIR", DEFAULT_BASE_DIR)
        self._base = Path(base)
        self._base.mkdir(parents=True, exist_ok=True)
        self._runs_path = self._base / "runs.jsonl"
        self._runs: dict[str, SimulationRun] = {}
        self._load()

    def _load(self) -> None:
        if not self._runs_path.exists():
            return
        with open(self._runs_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    run = SimulationRun.from_dict(rec)
                    self._runs[run.run_id] = run
                except Exception:
                    logger.exception("Skipping malformed simulation run line")

    def save_run(self, run: SimulationRun) -> str:
        run.authenticity = SIMULATED_AUTHENTICITY
        self._runs[run.run_id] = run
        self._rewrite()
        return run.run_id

    def get_run(self, run_id: str) -> SimulationRun | None:
        return self._runs.get(run_id)

    def list_runs(
        self, location_id: str | None = None, limit: int | None = None
    ) -> list[SimulationRun]:
        items = sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)
        if location_id:
            items = [r for r in items if r.location_id == location_id]
        return items[:limit] if limit else items

    def _rewrite(self) -> None:
        with open(self._runs_path, "w", encoding="utf-8") as f:
            for rec in self._runs.values():
                f.write(json.dumps(rec.to_dict(), sort_keys=True, default=str) + "\n")
