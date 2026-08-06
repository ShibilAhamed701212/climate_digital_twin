"""Phase 5 — ScenarioService (REAL counterfactual / what-if path).

Replaces the previous fake/hardcoded internals:
- no hardcoded ``{max_temp:30, min_temp:20, rainfall:50}`` fallback;
- no fallback fake weather when the baseline twin is missing (fails explicitly);
- ``run_scenario`` never treats ``scenario_id`` as ``location_id``;
- no empty Monte-Carlo / compare stubs in the REAL path.

Flow: REAL Twin baseline (authenticity must be REAL) → immutable snapshot →
ScenarioEngine (deterministic) → baseline OBSERVED hazard + SCENARIO hazard
(both non-persisting) → baseline-vs-scenario comparison → ScenarioStore.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from risk.evaluation.hazard_evaluator import HazardEvaluator
from risk.evaluation.twin_adapter import extract_twin_inputs

from climatedt.scenario.engine import ScenarioEngine
from climatedt.scenario.models import (
    SCENARIO_AUTHENTICITY,
    VARIABLE_UNITS,
    ScenarioComparison,
    ScenarioDefinition,
    ScenarioIntervention,
    ScenarioResult,
    compute_comparison_id,
    compute_result_id,
    new_scenario_id,
    serialize_hazard,
)
from climatedt.scenario.store import ScenarioStore

logger = logging.getLogger(__name__)


def _iso(dt: Any) -> str:
    if isinstance(dt, str):
        return dt
    if dt is None:
        return ""
    return dt.isoformat()


def _to_canonical(scenario: Any) -> ScenarioDefinition:
    """Convert a route/simulator scenario object (or canonical) to a canonical
    ``ScenarioDefinition`` with explicit interventions."""
    if isinstance(scenario, ScenarioDefinition):
        return scenario

    parameters = dict(getattr(scenario, "parameters", None) or {})

    location_id = getattr(scenario, "location_id", None) or parameters.get("location_id", "")
    duration_days = getattr(scenario, "duration_days", None) or parameters.get("duration_days", 0)
    latitude = getattr(scenario, "latitude", 0.0) or parameters.get("latitude", 0.0)
    longitude = getattr(scenario, "longitude", 0.0) or parameters.get("longitude", 0.0)

    interventions = _interventions_from(parameters)

    created_at = getattr(scenario, "created_at", "")
    if not isinstance(created_at, str):
        created_at = _iso(created_at)

    scenario_id = getattr(scenario, "scenario_id", "") or new_scenario_id()

    return ScenarioDefinition(
        scenario_id=scenario_id,
        name=getattr(scenario, "name", "Scenario"),
        description=getattr(scenario, "description", ""),
        scenario_type=getattr(scenario, "scenario_type", "custom"),
        location_id=location_id,
        interventions=interventions,
        duration_days=int(duration_days or 0),
        latitude=float(latitude or 0.0),
        longitude=float(longitude or 0.0),
        parameters=parameters,
        created_at=created_at,
    )


def _interventions_from(parameters: dict[str, Any]) -> list[ScenarioIntervention]:
    explicit = parameters.get("interventions")
    if isinstance(explicit, list) and explicit:
        parsed: list[ScenarioIntervention] = []
        for raw in explicit:
            if isinstance(raw, ScenarioIntervention):
                parsed.append(raw)
            elif isinstance(raw, dict):
                parsed.append(ScenarioIntervention.from_dict(raw))
        if parsed:
            return parsed

    built: list[ScenarioIntervention] = []
    if parameters.get("temperature_delta") is not None:
        built.append(
            ScenarioIntervention("temperature_2m", "ADD", float(parameters["temperature_delta"]))
        )
    if parameters.get("humidity_delta") is not None:
        built.append(
            ScenarioIntervention("humidity_pct", "ADD", float(parameters["humidity_delta"]))
        )
    if parameters.get("wind_speed_delta") is not None:
        built.append(
            ScenarioIntervention("wind_speed_10m", "ADD", float(parameters["wind_speed_delta"]))
        )
    if parameters.get("pressure_delta") is not None:
        built.append(
            ScenarioIntervention("pressure_hpa", "ADD", float(parameters["pressure_delta"]))
        )
    if parameters.get("rainfall_multiplier") is not None:
        built.append(
            ScenarioIntervention(
                "precipitation_mm", "MULTIPLY", float(parameters["rainfall_multiplier"])
            )
        )
    if parameters.get("rainfall_mm") is not None:
        built.append(
            ScenarioIntervention("precipitation_mm", "SET", float(parameters["rainfall_mm"]))
        )
    return built


def _hazard_deltas(
    baseline: Any,
    scenario: Any,
) -> dict[str, Any]:
    if baseline is None and scenario is None:
        return {}
    b_score = getattr(baseline, "hazard_score", 0.0) if baseline is not None else 0.0
    s_score = getattr(scenario, "hazard_score", 0.0) if scenario is not None else 0.0
    b_type = getattr(baseline, "hazard_type", "unknown") if baseline is not None else "unknown"
    s_type = getattr(scenario, "hazard_type", "unknown") if scenario is not None else "unknown"
    b_sev = (
        getattr(getattr(baseline, "severity", None), "value", "NONE")
        if baseline is not None
        else "NONE"
    )
    s_sev = (
        getattr(getattr(scenario, "severity", None), "value", "NONE")
        if scenario is not None
        else "NONE"
    )
    return {
        "baseline_hazard": b_type,
        "baseline_score": round(b_score, 2),
        "baseline_severity": b_sev,
        "scenario_hazard": s_type,
        "scenario_score": round(s_score, 2),
        "scenario_severity": s_sev,
        "delta": round(s_score - b_score, 2),
    }


class ScenarioDefinitionGenerator:
    """Builds canonical scenario definitions.  Used by the legacy
    ``/scenario/generate/{template}`` route (demo)."""

    def _base(
        self,
        scenario_id: str,
        name: str,
        description: str,
        scenario_type: str,
        location_id: str,
        interventions: list[ScenarioIntervention],
        duration_days: int,
        parameters: dict[str, Any] | None = None,
    ) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id=scenario_id,
            name=name,
            description=description,
            scenario_type=scenario_type,
            location_id=location_id,
            interventions=interventions,
            duration_days=duration_days,
            parameters=parameters or {},
        )

    def warming_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        delta: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        return self._base(
            scenario_id=f"warming_{new_scenario_id().split('_')[-1]}",
            name=f"+{delta:g}°C Warming",
            description=f"Temperature increase of {delta:g}°C for {duration_days} days",
            scenario_type="temperature",
            location_id=location_id,
            interventions=[ScenarioIntervention("temperature_2m", "ADD", delta)],
            duration_days=duration_days,
            parameters={"temperature_delta": delta, "duration_days": duration_days},
        )

    def rainfall_scenario(
        self,
        location_id: str,
        latitude: float,
        longitude: float,
        multiplier: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        change_pct = round((multiplier - 1.0) * 100, 1)
        return self._base(
            scenario_id=f"rainfall_{new_scenario_id().split('_')[-1]}",
            name=f"Rainfall {change_pct:+.0f}%",
            description=f"Rainfall change of {change_pct:+.0f}% for {duration_days} days",
            scenario_type="rainfall",
            location_id=location_id,
            interventions=[ScenarioIntervention("precipitation_mm", "MULTIPLY", multiplier)],
            duration_days=duration_days,
            parameters={"rainfall_change_pct": change_pct, "duration_days": duration_days},
        )

    def extreme_scenario(
        self, location_id: str, latitude: float, longitude: float, duration_days: int = 30
    ) -> ScenarioDefinition:
        return self._base(
            scenario_id=f"extreme_{new_scenario_id().split('_')[-1]}",
            name="Extreme Worst-Case",
            description=f"Extreme scenario for {duration_days} days",
            scenario_type="extreme_event",
            location_id=location_id,
            interventions=[
                ScenarioIntervention("temperature_2m", "ADD", 4.0),
                ScenarioIntervention("precipitation_mm", "MULTIPLY", 1.3),
            ],
            duration_days=duration_days,
            parameters={"event_type": "heatwave", "temperature_delta": 4.0},
        )

    def drought_scenario(
        self, location_id: str, latitude: float, longitude: float, duration_days: int = 90
    ) -> ScenarioDefinition:
        return self._base(
            scenario_id=f"drought_{new_scenario_id().split('_')[-1]}",
            name="Drought Conditions",
            description=f"Drought scenario for {duration_days} days",
            scenario_type="extreme_event",
            location_id=location_id,
            interventions=[
                ScenarioIntervention("temperature_2m", "ADD", 2.0),
                ScenarioIntervention("precipitation_mm", "MULTIPLY", 0.2),
            ],
            duration_days=duration_days,
            parameters={"event_type": "drought", "rainfall_change_pct": -80.0},
        )

    def ipcc_scenario(
        self, location_id: str, latitude: float, longitude: float, pathway: str, year: int
    ) -> ScenarioDefinition:
        return self._base(
            scenario_id=f"ipcc_{new_scenario_id().split('_')[-1]}",
            name=f"IPCC {pathway.upper()} ({year})",
            description=f"IPCC scenario {pathway} for year {year}",
            scenario_type="temperature",
            location_id=location_id,
            interventions=[ScenarioIntervention("temperature_2m", "ADD", 2.0)],
            duration_days=30,
            parameters={"pathway": pathway, "target_year": year, "temperature_delta": 2.0},
        )

    def custom_scenario(
        self,
        name: str,
        description: str,
        location_id: str,
        latitude: float,
        longitude: float,
        parameters: dict[str, Any],
        duration_days: int,
    ) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id=f"custom_{new_scenario_id().split('_')[-1]}",
            name=name,
            description=description,
            scenario_type="custom",
            location_id=location_id,
            interventions=_interventions_from(parameters),
            duration_days=duration_days,
            parameters=parameters,
        )

    def validate_scenario(self, _scenario: ScenarioDefinition) -> list[str]:
        return []


class ScenarioService:
    """Real counterfactual scenario service."""

    def __init__(
        self,
        engine: ScenarioEngine | None = None,
        store: ScenarioStore | None = None,
        evaluator: HazardEvaluator | None = None,
        twin_manager: Any | None = None,
        generator: ScenarioDefinitionGenerator | None = None,
    ) -> None:
        self._engine = engine or ScenarioEngine()
        self._store = store or ScenarioStore()
        self._evaluator = evaluator or HazardEvaluator()
        self._twin_manager = twin_manager
        self.generator = generator or ScenarioDefinitionGenerator()

    async def save_scenario(self, scenario: Any) -> str:
        definition = _to_canonical(scenario)
        return self._store.save_definition(definition)

    async def load_scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        return self._store.get_definition(scenario_id)

    async def list_scenarios(self, limit: int | None = None) -> list[ScenarioDefinition]:
        return self._store.list_definitions(limit)

    async def list_results(
        self, scenario_id: str | None = None, limit: int | None = None
    ) -> list[ScenarioResult]:
        return self._store.list_results(scenario_id, limit)

    async def run_scenario(self, scenario: Any) -> ScenarioResult:
        started = time.perf_counter()
        definition = _to_canonical(scenario)
        if not definition.location_id:
            raise ValueError("Scenario has no location_id; cannot run against a REAL twin")

        baseline = await self._get_twin_state(definition.location_id)
        if baseline is None:
            raise ValueError(
                f"No authoritative REAL twin state available for "
                f"'{definition.location_id}'; refusing to substitute hardcoded weather"
            )
        if getattr(baseline, "authenticity", "REAL").upper() != "REAL":
            raise ValueError(
                f"Baseline twin for '{definition.location_id}' is not authoritative "
                f"REAL state (authenticity={getattr(baseline, 'authenticity', '?')})"
            )

        engine_result = self._engine.apply(
            baseline,
            definition.interventions,
            scenario_id=definition.scenario_id,
            description=definition.description,
        )

        baseline_inputs = extract_twin_inputs(baseline)
        scenario_inputs = extract_twin_inputs(engine_result.state)

        baseline_hazard = self._evaluator.assess_observed(baseline_inputs, definition.location_id)
        scenario_hazard = self._evaluator.assess_scenario(scenario_inputs, definition.location_id)

        baseline_state: dict[str, float] = {}
        for var in VARIABLE_UNITS:
            value = getattr(baseline, var, None)
            if value is not None:
                baseline_state[var] = float(value)

        baseline_timestamp = _iso(getattr(baseline, "timestamp", None))
        result_id = compute_result_id(definition, baseline.entity_id, baseline_timestamp)

        result = ScenarioResult(
            result_id=result_id,
            scenario_id=definition.scenario_id,
            definition=definition,
            location_id=definition.location_id,
            baseline_twin_version=baseline.entity_id,
            baseline_timestamp=baseline_timestamp,
            baseline_state=baseline_state,
            scenario_state=dict(engine_result.applied_values),
            deltas=dict(engine_result.deltas),
            baseline_hazard=serialize_hazard(baseline_hazard),
            scenario_hazard=serialize_hazard(scenario_hazard),
            hazard_deltas=_hazard_deltas(baseline_hazard, scenario_hazard),
            authenticity=SCENARIO_AUTHENTICITY,
            mode="REAL",
            execution_time_ms=round((time.perf_counter() - started) * 1000.0, 3),
        )
        self._store.save_result(result)
        logger.info(
            "Scenario %s run for %s -> %s (scenario hazard %s/%s)",
            definition.scenario_id,
            definition.location_id,
            result_id,
            result.hazard_deltas.get("scenario_hazard"),
            result.hazard_deltas.get("scenario_score"),
        )
        return result

    async def compare_scenarios(
        self,
        scenarios: list[Any],
    ) -> list[ScenarioComparison]:
        if len(scenarios) < 2:
            return []
        results = [await self.run_scenario(s) for s in scenarios]
        baseline = results[0]
        comparisons: list[ScenarioComparison] = []
        for r in results[1:]:
            variable_deltas: dict[str, float] = {}
            percentage_changes: dict[str, float] = {}
            for var in VARIABLE_UNITS:
                b = baseline.scenario_state.get(var)
                s = r.scenario_state.get(var)
                if b is None or s is None:
                    continue
                variable_deltas[var] = round(s - b, 2)
                if b != 0:
                    percentage_changes[var] = round((s - b) / b * 100.0, 2)
            significant = [v for v, d in variable_deltas.items() if abs(d) > 1e-9]

            b_score = baseline.hazard_deltas.get("scenario_score", 0.0)
            s_score = r.hazard_deltas.get("scenario_score", 0.0)
            hazard_deltas = {
                "baseline_hazard": baseline.hazard_deltas.get("scenario_hazard"),
                "scenario_hazard": r.hazard_deltas.get("scenario_hazard"),
                "delta": round(float(s_score) - float(b_score), 2),
            }
            summary = (
                f"Scenario '{r.scenario_id}' vs baseline '{baseline.scenario_id}': "
                f"variable deltas {variable_deltas}; hazard delta "
                f"{hazard_deltas['delta']}"
            )
            comparisons.append(
                ScenarioComparison(
                    comparison_id=compute_comparison_id(baseline.result_id, r.result_id),
                    baseline_result_id=baseline.result_id,
                    scenario_result_id=r.result_id,
                    variable_deltas=variable_deltas,
                    percentage_changes=percentage_changes,
                    significant_variables=significant,
                    summary=summary,
                    hazard_deltas=hazard_deltas,
                )
            )
        return comparisons

    async def run_monte_carlo_scenario(
        self,
        _scenario: Any,
        _distributions: dict[str, Any] | None = None,
    ) -> Any:
        """Legacy demo Monte-Carlo stub.  Returns no-op result tagged DEMO.

        ponytail: kept as a stub (mode=DEMO); probabilistic Monte Carlo is part
        of the demo stack on :8002 and is out of scope for the REAL path.
        """

        class _MCResult:
            num_samples = 0
            statistics: dict[str, Any] = {}
            mode = "DEMO"
            authenticity = SCENARIO_AUTHENTICITY

        return _MCResult()

    async def _get_twin_state(self, location_id: str) -> Any:
        try:
            if self._twin_manager is None:
                from climatedt.twin.state_manager import TwinStateManager

                self._twin_manager = TwinStateManager()
            return await self._twin_manager.get_current_state(location_id)
        except ValueError:
            logger.info("No twin state found for %s", location_id)
            return None
        except Exception as exc:
            logger.warning("Failed to get twin state for %s: %s", location_id, exc)
            return None
