import logging
import uuid
from datetime import datetime
from typing import Any

from simulator.engine.scenario_engine import ScenarioEngine
from simulator.engine.twin_engine import DigitalTwinEngine
from simulator.models.scenario_models import ScenarioDefinition
from simulator.scenarios.scenario_builder import (
    create_scenario,
    get_preset_scenario,
)

logger = logging.getLogger(__name__)


class _SimulationResult:
    def __init__(self) -> None:
        self.result_id = ""
        self.scenario_id = ""
        self.location_id = ""
        self.summary_statistics: dict[str, Any] = {}
        self.time_steps: list[datetime] = []
        self.execution_time_ms = 0.0


class _ScenarioComparison:
    def __init__(self) -> None:
        self.comparison_id = ""
        self.baseline_result_id = ""
        self.scenario_result_id = ""
        self.variable_deltas: dict[str, float] = {}
        self.percentage_changes: dict[str, float] = {}
        self.significant_variables: list[str] = []
        self.summary = ""


class _MonteCarloResult:
    def __init__(self) -> None:
        self.num_samples = 0
        self.statistics: dict[str, Any] = {}


class _ScenarioGenerator:
    def warming_scenario(
        self,
        _location_id: str,
        _latitude: float,
        _longitude: float,
        delta: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        return create_scenario(
            scenario_id=f"warming_{uuid.uuid4().hex[:8]}",
            name=f"+{delta}°C Warming",
            description=f"Temperature increase of {delta}°C for {duration_days} days",
            scenario_type="temperature",
            parameters={"temperature_delta": delta, "duration_days": duration_days},
        )

    def rainfall_scenario(
        self,
        _location_id: str,
        _latitude: float,
        _longitude: float,
        multiplier: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        change_pct = round((multiplier - 1.0) * 100, 1)
        return create_scenario(
            scenario_id=f"rainfall_{uuid.uuid4().hex[:8]}",
            name=f"Rainfall {change_pct:+.0f}%",
            description=f"Rainfall change of {change_pct:+.0f}% for {duration_days} days",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": change_pct, "duration_days": duration_days},
        )

    def extreme_scenario(
        self,
        _location_id: str,
        _latitude: float,
        _longitude: float,
        duration_days: int = 30,
    ) -> ScenarioDefinition:
        return create_scenario(
            scenario_id=f"extreme_{uuid.uuid4().hex[:8]}",
            name="Extreme Worst-Case",
            description=f"Extreme scenario for {duration_days} days",
            scenario_type="extreme_event",
            parameters={
                "event_type": "heatwave",
                "temperature_delta": 4.0,
                "duration_days": duration_days,
            },
        )

    def drought_scenario(
        self,
        _location_id: str,
        _latitude: float,
        _longitude: float,
        duration_days: int = 90,
    ) -> ScenarioDefinition:
        return create_scenario(
            scenario_id=f"drought_{uuid.uuid4().hex[:8]}",
            name="Drought Conditions",
            description=f"Drought scenario for {duration_days} days",
            scenario_type="extreme_event",
            parameters={
                "event_type": "drought",
                "rainfall_change_pct": -80.0,
                "duration_days": duration_days,
            },
        )

    def ipcc_scenario(
        self,
        _location_id: str,
        _latitude: float,
        _longitude: float,
        pathway: str,
        year: int,
    ) -> ScenarioDefinition:
        return create_scenario(
            scenario_id=f"ipcc_{uuid.uuid4().hex[:8]}",
            name=f"IPCC {pathway.upper()} ({year})",
            description=f"IPCC scenario {pathway} for year {year}",
            scenario_type="temperature",
            parameters={"pathway": pathway, "target_year": year, "temperature_delta": 2.0},
        )


class ScenarioService:
    def __init__(self) -> None:
        self._twin = DigitalTwinEngine()
        self._scenarios: dict[str, ScenarioDefinition] = {}
        self._engine = ScenarioEngine()
        self.generator = _ScenarioGenerator()

    async def save_scenario(self, scenario: ScenarioDefinition) -> str:
        sid = scenario.scenario_id or f"scenario_{uuid.uuid4().hex[:8]}"
        self._scenarios[sid] = scenario
        logger.info("Scenario saved: %s", sid)
        return sid

    async def load_scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            scenario = get_preset_scenario(scenario_id)
        return scenario

    async def run_scenario(self, scenario: ScenarioDefinition) -> _SimulationResult:
        baseline = self._collect_baseline(location_ids=[scenario.scenario_id])
        run = self._engine.run_simulation(scenario, baseline)
        result = _SimulationResult()
        result.scenario_id = scenario.scenario_id
        result.execution_time_ms = run.total_duration_ms
        return result

    async def run_monte_carlo_scenario(
        self,
        _scenario: ScenarioDefinition,
        _distributions: dict[str, Any] | None = None,
    ) -> _MonteCarloResult:
        return _MonteCarloResult()

    async def compare_scenarios(
        self,
        _scenarios: list[ScenarioDefinition],
    ) -> list[_ScenarioComparison]:
        return []

    def _collect_baseline(self, location_ids: list[str] | None = None) -> list[dict[str, Any]]:
        all_location_ids = self._twin.state_manager.get_all_location_ids()
        if location_ids:
            ids = [lid for lid in location_ids if lid in all_location_ids]
        else:
            ids = list(all_location_ids)
        baseline: list[dict[str, Any]] = []
        for loc_id in ids:
            state = self._twin.get_current_state(loc_id)
            if state:
                baseline.append(
                    {**state, "location_id": loc_id}
                    | {"max_temp": 30.0, "min_temp": 20.0, "rainfall": 50.0}
                )
        if not baseline:
            baseline = [
                {"location_id": lid, "max_temp": 30.0, "min_temp": 20.0, "rainfall": 50.0}
                for lid in (ids or ["KA-BLR-001", "KA-MYS-001"])
            ]
        return baseline
