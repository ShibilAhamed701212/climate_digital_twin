"""Core simulation execution logic for what-if climate scenarios."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from simulator.models.scenario_models import ScenarioDefinition, ScenarioRun, SimulationResult


class ScenarioEngine:
    """Deterministic scenario simulation engine.

    Applies scenario parameters to baseline climate data to produce
    simulated climate states with calculated deltas.
    """

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed

    def run_simulation(
        self,
        scenario: ScenarioDefinition,
        baseline_data: list[dict[str, Any]],
    ) -> ScenarioRun:
        """Execute a scenario simulation across all baseline locations.

        Returns a ScenarioRun with results for every location.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now().isoformat()
        start_ms = time.perf_counter()

        location_count = len(baseline_data)
        results: list[SimulationResult] = []

        for baseline in baseline_data:
            result = self._simulate_single(scenario, baseline)
            results.append(result)

        end_ms = time.perf_counter()
        total_duration_ms = (end_ms - start_ms) * 1000

        return ScenarioRun(
            run_id=run_id,
            scenario=scenario,
            results=results,
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
            total_duration_ms=round(total_duration_ms, 2),
            location_count=location_count,
            status="completed",
        )

    def _simulate_single(
        self,
        scenario: ScenarioDefinition,
        baseline: dict[str, Any],
    ) -> SimulationResult:
        """Simulate a single location under the given scenario."""
        location_id = baseline.get("location_id", "unknown")
        timestamp = datetime.now().isoformat()
        start_ms = time.perf_counter()

        try:
            params = scenario.parameters

            if scenario.scenario_type == "combined":
                sub_scenarios_list = params.get("scenarios", [])
                simulated = dict(baseline)
                for sub in sub_scenarios_list:
                    sub_type = sub.get("scenario_type", "")
                    sub_params = sub.get("parameters", {})
                    simulated = self._apply_modifications(simulated, sub_type, sub_params)
            else:
                simulated = self._apply_modifications(
                    dict(baseline), scenario.scenario_type, params
                )

            simulated["state_type"] = "scenario"
            simulated["scenario_id"] = scenario.scenario_id
            simulated["timestamp"] = timestamp

            deltas = self._compute_deltas(baseline, simulated)
            end_ms = time.perf_counter()
            duration_ms = (end_ms - start_ms) * 1000

            return SimulationResult(
                location_id=location_id,
                scenario_id=scenario.scenario_id,
                timestamp=timestamp,
                baseline=baseline,
                simulated=simulated,
                deltas=deltas,
                duration_ms=round(duration_ms, 2),
                success=True,
            )

        except Exception as e:
            end_ms = time.perf_counter()
            duration_ms = (end_ms - start_ms) * 1000
            return SimulationResult(
                location_id=location_id,
                scenario_id=scenario.scenario_id,
                timestamp=timestamp,
                baseline=baseline,
                simulated={},
                deltas={},
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(e),
            )

    def _apply_modifications(
        self,
        data: dict[str, Any],
        scenario_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply scenario modifications to a copy of the baseline data."""
        result = dict(data)

        if scenario_type == "temperature":
            delta = params.get("temperature_delta", 0)
            if isinstance(delta, int | float):
                if "max_temp" in result:
                    result["max_temp"] = round(float(result["max_temp"]) + delta, 2)
                if "min_temp" in result:
                    result["min_temp"] = round(float(result["min_temp"]) + delta, 2)

        elif scenario_type == "rainfall":
            pct = params.get("rainfall_change_pct", 0)
            if isinstance(pct, int | float) and "rainfall" in result:
                result["rainfall"] = round(max(0, float(result["rainfall"]) * (1 + pct / 100)), 2)

        elif scenario_type == "monsoon":
            delay = params.get("delay_days", 0)
            intensity = params.get("intensity_reduction_pct", 0)
            result["monsoon_delay_days"] = delay
            if intensity and "rainfall" in result:
                factor = (100 - float(intensity)) / 100
                result["rainfall"] = round(float(result["rainfall"]) * factor, 2)

        elif scenario_type == "extreme_event":
            event_type = params.get("event_type", "")
            if event_type == "heatwave":
                delta = params.get("temperature_delta", 5.0)
                if "max_temp" in result:
                    result["max_temp"] = round(float(result["max_temp"]) + delta, 2)
                if "min_temp" in result:
                    result["min_temp"] = round(float(result["min_temp"]) + delta * 0.5, 2)
            elif event_type == "flood":
                pct = params.get("rainfall_change_pct", 200.0)
                if "rainfall" in result:
                    result["rainfall"] = round(float(result["rainfall"]) * (1 + pct / 100), 2)
            elif event_type == "drought":
                pct = params.get("rainfall_change_pct", -80.0)
                if "rainfall" in result:
                    result["rainfall"] = round(
                        max(0, float(result["rainfall"]) * (1 + pct / 100)), 2
                    )

        result["prediction_confidence"] = round(
            float(result.get("prediction_confidence", 0.5)) * 0.9, 3
        )
        result["data_source"] = "scenario"

        return result

    @staticmethod
    def _compute_deltas(
        baseline: dict[str, Any],
        simulated: dict[str, Any],
    ) -> dict[str, float]:
        """Calculate deltas between baseline and simulated for numeric fields."""
        delta_keys = {"rainfall", "max_temp", "min_temp", "risk_score"}
        deltas: dict[str, float] = {}
        for key in delta_keys:
            b_val = baseline.get(key)
            s_val = simulated.get(key)
            if b_val is not None and s_val is not None:
                from contextlib import suppress

                with suppress(TypeError, ValueError):
                    deltas[key] = round(float(s_val) - float(b_val), 2)
        return deltas

    @staticmethod
    def compare_with_baseline(
        run: ScenarioRun,
    ) -> list[dict[str, Any]]:
        """Generate a per-location comparison summary."""
        summaries: list[dict[str, Any]] = []
        for result in run.results:
            summaries.append(
                {
                    "location_id": result.location_id,
                    "baseline_rainfall": result.baseline.get("rainfall", 0),
                    "simulated_rainfall": result.simulated.get("rainfall", 0),
                    "delta_rainfall": result.deltas.get("rainfall", 0),
                    "baseline_max_temp": result.baseline.get("max_temp", 0),
                    "simulated_max_temp": result.simulated.get("max_temp", 0),
                    "delta_max_temp": result.deltas.get("max_temp", 0),
                    "baseline_min_temp": result.baseline.get("min_temp", 0),
                    "simulated_min_temp": result.simulated.get("min_temp", 0),
                    "delta_min_temp": result.deltas.get("min_temp", 0),
                    "success": result.success,
                }
            )
        return summaries
