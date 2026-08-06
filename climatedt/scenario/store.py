"""Phase 5 — ScenarioStore.

JSONL persistence under ``data/scenarios/`` for scenario definitions and results.
Never writes to ObservationStore / ForecastStore / the Twin repository /
HazardStore / AlertStore.  Loads existing files on init (restart recovery).
Saves are idempotent on the content-hash identity (``scenario_id`` / ``result_id``).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from climatedt.scenario.models import (
    SCENARIO_AUTHENTICITY,
    ScenarioDefinition,
    ScenarioResult,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_DIR = "data/scenarios"


class ScenarioStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        base = base_dir or os.environ.get("CLIMATEDT_SCENARIO_DIR", DEFAULT_BASE_DIR)
        self._base = Path(base)
        self._base.mkdir(parents=True, exist_ok=True)
        self._definitions_path = self._base / "definitions.jsonl"
        self._results_path = self._base / "results.jsonl"
        self._definitions: dict[str, ScenarioDefinition] = {}
        self._results: dict[str, ScenarioResult] = {}
        self._load()

    # ── load / recover ────────────────────────────────────────────────────

    def _load(self) -> None:
        for line in self._read_jsonl(self._definitions_path):
            try:
                d = ScenarioDefinition.from_dict(line)
                if d.authenticity != SCENARIO_AUTHENTICITY:
                    logger.warning(
                        "Definition %s has authenticity %r — relabelling to SCENARIO",
                        d.scenario_id,
                        d.authenticity,
                    )
                self._definitions[d.scenario_id] = d
            except Exception:
                logger.exception("Skipping malformed scenario definition line")
        for line in self._read_jsonl(self._results_path):
            try:
                r = ScenarioResult.from_dict(line)
                self._results[r.result_id] = r
            except Exception:
                logger.exception("Skipping malformed scenario result line")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        return out

    # ── definitions ───────────────────────────────────────────────────────

    def save_definition(self, definition: ScenarioDefinition) -> str:
        definition = ScenarioDefinition(
            scenario_id=definition.scenario_id,
            name=definition.name,
            description=definition.description,
            scenario_type=definition.scenario_type,
            location_id=definition.location_id,
            interventions=list(definition.interventions),
            duration_days=definition.duration_days,
            latitude=definition.latitude,
            longitude=definition.longitude,
            parameters=dict(definition.parameters),
            method=definition.method,
            method_version=definition.method_version,
            config_version=definition.config_version,
            authenticity=SCENARIO_AUTHENTICITY,
            created_at=definition.created_at,
        )
        self._definitions[definition.scenario_id] = definition
        self._rewrite(self._definitions_path, [d.to_dict() for d in self._definitions.values()])
        return definition.scenario_id

    def get_definition(self, scenario_id: str) -> ScenarioDefinition | None:
        return self._definitions.get(scenario_id)

    def list_definitions(self, limit: int | None = None) -> list[ScenarioDefinition]:
        items = sorted(self._definitions.values(), key=lambda d: d.created_at, reverse=True)
        return items[:limit] if limit else items

    # ── results ───────────────────────────────────────────────────────────

    def save_result(self, result: ScenarioResult) -> str:
        result = ScenarioResult(
            result_id=result.result_id,
            scenario_id=result.scenario_id,
            definition=result.definition,
            location_id=result.location_id,
            baseline_twin_version=result.baseline_twin_version,
            baseline_timestamp=result.baseline_timestamp,
            baseline_state=dict(result.baseline_state),
            scenario_state=dict(result.scenario_state),
            deltas=dict(result.deltas),
            baseline_hazard=result.baseline_hazard,
            scenario_hazard=result.scenario_hazard,
            hazard_deltas=dict(result.hazard_deltas),
            authenticity=SCENARIO_AUTHENTICITY,
            mode=result.mode,
            execution_time_ms=result.execution_time_ms,
            created_at=result.created_at,
        )
        self._results[result.result_id] = result
        self._rewrite(self._results_path, [r.to_dict() for r in self._results.values()])
        return result.result_id

    def get_result(self, result_id: str) -> ScenarioResult | None:
        return self._results.get(result_id)

    def list_results(
        self, scenario_id: str | None = None, limit: int | None = None
    ) -> list[ScenarioResult]:
        items = sorted(self._results.values(), key=lambda r: r.created_at, reverse=True)
        if scenario_id:
            items = [r for r in items if r.scenario_id == scenario_id]
        return items[:limit] if limit else items

    # ── internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _rewrite(path: Path, records: list[dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
