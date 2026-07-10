"""Ensemble simulation engine for multi-configuration scenario analysis.

Each ensemble member can differ in model parameters, perturbation intensity,
initial conditions, or temporal patterns. Provides ensemble mean, spread,
member ranking, and exceedance probabilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from simulator.engine.perturbation import PerturbationEngine
from simulator.models.scenario_models import ScenarioDefinition, SimulationResult
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)


@dataclass
class EnsembleResult:
    n_members: int
    members: list[SimulationResult]
    ensemble_mean: dict[str, list[float]] = field(default_factory=dict)
    ensemble_spread: dict[str, list[float]] = field(default_factory=dict)
    member_rankings: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    exceedance_probabilities: dict[tuple[str, float], float] = field(default_factory=dict)
    summary: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.n_members <= 0:
            raise ValueError(f"n_members must be positive, got {self.n_members}")
        if len(self.members) != self.n_members:
            raise ValueError(
                f"Number of members ({len(self.members)}) must match n_members ({self.n_members})"
            )


class EnsembleSimulator:
    def __init__(
        self,
        perturbation_engine: PerturbationEngine,
        n_members: int = 10,
    ) -> None:
        if n_members <= 0:
            raise ValueError(f"n_members must be positive, got {n_members}")
        self._perturbation = perturbation_engine
        self._n_members = n_members
        _logger.debug("EnsembleSimulator initialized (n_members=%d)", n_members)

    @property
    def n_members(self) -> int:
        return self._n_members

    async def run_ensemble(
        self,
        base_data: list[WeatherObservation],
        base_scenario: ScenarioDefinition,
    ) -> EnsembleResult:
        if not base_data:
            raise ValueError("Cannot run ensemble on empty base data")

        _logger.info(
            "Running ensemble simulation: %d members, %d base observations",
            self._n_members,
            len(base_data),
        )

        import time

        members: list[SimulationResult] = []
        for member_idx in range(self._n_members):
            start_ms = time.perf_counter()
            member_scenario = self._build_member_scenario(base_scenario, member_idx)
            perturbed = self._perturbation.apply_perturbation(base_data, member_scenario)

            time_steps = [obs.timestamp for obs in perturbed]
            time_series: dict[str, list[float]] = {
                "temperature_2m": [o.temperature_2m for o in perturbed],
                "precipitation_mm": [o.precipitation_mm for o in perturbed],
                "humidity_pct": [o.humidity_pct for o in perturbed],
                "pressure_hpa": [o.pressure_hpa for o in perturbed],
                "wind_speed_10m": [o.wind_speed_10m for o in perturbed],
            }

            summary_statistics: dict[str, dict[str, float]] = {}
            for var_name, values in time_series.items():
                arr = np.array(values, dtype=np.float64)
                summary_statistics[var_name] = {
                    "mean": float(np.mean(arr)),
                    "max": float(np.max(arr)),
                    "min": float(np.min(arr)),
                    "std": float(np.std(arr)),
                }

            end_ms = time.perf_counter()
            duration_ms = (end_ms - start_ms) * 1000

            result = SimulationResult(
                location_id=base_scenario.parameters.get(
                    "location_id", base_data[0].location_id if base_data else "unknown"
                ),
                scenario_id=member_scenario.scenario_id,
                timestamp=datetime.now(UTC).isoformat(),
                baseline={
                    "location_id": base_data[0].location_id if base_data else "unknown",
                    "data_source": "ensemble_baseline",
                },
                simulated={
                    "time_series": time_series,
                    "time_steps": [t.isoformat() for t in time_steps],
                    "summary_statistics": summary_statistics,
                    "ensemble_member": str(member_idx),
                    "data_source": "ensemble",
                },
                deltas={},
                duration_ms=round(duration_ms, 2),
                success=True,
            )
            members.append(result)

        ensemble_mean = self.compute_ensemble_mean(members)
        ensemble_spread = self.compute_ensemble_spread(members)
        member_rankings = self._compute_rankings(members)
        summary = self._compute_summary(members)

        return EnsembleResult(
            n_members=self._n_members,
            members=members,
            ensemble_mean=ensemble_mean,
            ensemble_spread=ensemble_spread,
            member_rankings=member_rankings,
            exceedance_probabilities={},
            summary=summary,
        )

    def compute_ensemble_stats(self, results: list[SimulationResult]) -> dict[str, Any]:
        if not results:
            return {}

        var_values: dict[str, list[float]] = {}
        for result in results:
            summary_stats = result.simulated.get("summary_statistics", {})
            for var_name, stats in summary_stats.items():
                mean_val = stats.get("mean", 0.0)
                if var_name not in var_values:
                    var_values[var_name] = []
                var_values[var_name].append(mean_val)

        stats: dict[str, Any] = {
            "variable_means": {},
            "variable_stds": {},
            "n_members": len(results),
        }

        for var_name, values in var_values.items():
            arr = np.array(values, dtype=np.float64)
            stats["variable_means"][var_name] = float(np.mean(arr))
            stats["variable_stds"][var_name] = float(np.std(arr))

        return stats

    def probability_of_exceedance(
        self,
        results: list[SimulationResult],
        variable: str,
        threshold: float,
    ) -> float:
        if not results:
            return 0.0

        exceed_count = 0
        total = 0

        for result in results:
            time_series = result.simulated.get("time_series", {})
            values = time_series.get(variable, [])
            if values:
                total += 1
                mean_val = np.mean(values)
                if mean_val > threshold:
                    exceed_count += 1

        return exceed_count / total if total > 0 else 0.0

    def rank_members(
        self,
        results: list[SimulationResult],
        variable: str,
    ) -> list[tuple[str, float]]:
        rankings: list[tuple[str, float]] = []

        for result in results:
            time_series = result.simulated.get("time_series", {})
            values = time_series.get(variable, [])
            if values:
                mean_val = float(np.mean(values))
                rankings.append((result.scenario_id, mean_val))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def compute_ensemble_mean(
        self,
        results: list[SimulationResult],
    ) -> dict[str, list[float]]:
        if not results:
            return {}

        first_ts = results[0].simulated.get("time_series", {})
        variables = list(first_ts.keys())
        ensemble_mean: dict[str, list[float]] = {}

        for var_name in variables:
            member_values: list[list[float]] = []
            for result in results:
                ts = result.simulated.get("time_series", {})
                if var_name in ts:
                    member_values.append(ts[var_name])

            if member_values:
                arr = np.array(member_values, dtype=np.float64)
                ensemble_mean[var_name] = list(np.mean(arr, axis=0))

        return ensemble_mean

    def compute_ensemble_spread(
        self,
        results: list[SimulationResult],
    ) -> dict[str, list[float]]:
        if not results:
            return {}

        first_ts = results[0].simulated.get("time_series", {})
        variables = list(first_ts.keys())
        ensemble_spread: dict[str, list[float]] = {}

        for var_name in variables:
            member_values: list[list[float]] = []
            for result in results:
                ts = result.simulated.get("time_series", {})
                if var_name in ts:
                    member_values.append(ts[var_name])

            if member_values:
                arr = np.array(member_values, dtype=np.float64)
                ensemble_spread[var_name] = list(np.std(arr, axis=0))

        return ensemble_spread

    def _build_member_scenario(
        self,
        base_scenario: ScenarioDefinition,
        member_idx: int,
    ) -> ScenarioDefinition:
        rng = np.random.default_rng(seed=member_idx)

        base_params = dict(base_scenario.parameters)
        temp_delta = base_params.get("temperature_delta")
        rain_mult = base_params.get("rainfall_multiplier")
        humid_delta = base_params.get("humidity_delta")
        wind_delta = base_params.get("wind_speed_delta")
        press_delta = base_params.get("pressure_delta")

        delta_fields = {
            "temperature_delta": (0.1, temp_delta),
            "humidity_delta": (0.5, humid_delta),
            "wind_speed_delta": (0.2, wind_delta),
            "pressure_delta": (0.3, press_delta),
        }

        params = dict(base_params)
        for field_name, (noise_std, base_val) in delta_fields.items():
            if base_val is not None:
                variation = rng.normal(0, noise_std)
                params[field_name] = base_val + variation

        if rain_mult is not None:
            multiplier_var = rng.lognormal(mean=0, sigma=0.05)
            params["rainfall_multiplier"] = rain_mult * multiplier_var

        return ScenarioDefinition(
            scenario_id=base_scenario.scenario_id,
            name=f"{base_scenario.name} (member {member_idx})",
            description=f"Ensemble member {member_idx}: {base_scenario.description}",
            scenario_type=base_scenario.scenario_type,
            parameters=params,
        )

    def _compute_rankings(
        self,
        results: list[SimulationResult],
    ) -> dict[str, list[tuple[str, float]]]:
        if not results:
            return {}

        first_ts = results[0].simulated.get("time_series", {})
        variables = list(first_ts.keys())
        rankings: dict[str, list[tuple[str, float]]] = {}

        for var_name in variables:
            rankings[var_name] = self.rank_members(results, var_name)

        return rankings

    @staticmethod
    def _compute_summary(
        results: list[SimulationResult],
    ) -> dict[str, dict[str, float]]:
        if not results:
            return {}

        var_means: dict[str, list[float]] = {}
        for result in results:
            summary_stats = result.simulated.get("summary_statistics", {})
            for var_name, stats in summary_stats.items():
                mean_val = stats.get("mean", 0.0)
                if var_name not in var_means:
                    var_means[var_name] = []
                var_means[var_name].append(mean_val)

        summary: dict[str, dict[str, float]] = {}
        for var_name, values in var_means.items():
            arr = np.array(values, dtype=np.float64)
            summary[var_name] = {
                "ensemble_mean": float(np.mean(arr)),
                "ensemble_std": float(np.std(arr)),
                "ensemble_min": float(np.min(arr)),
                "ensemble_max": float(np.max(arr)),
                "ensemble_p5": float(np.percentile(arr, 5)),
                "ensemble_p50": float(np.percentile(arr, 50)),
                "ensemble_p95": float(np.percentile(arr, 95)),
            }

        return summary


__all__ = [
    "EnsembleSimulator",
    "EnsembleResult",
]
