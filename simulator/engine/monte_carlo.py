"""Monte Carlo simulation engine for probabilistic scenario analysis.

Supports multiple sampling distributions (normal, uniform, log-normal,
triangular) and provides confidence intervals, sensitivity analysis,
and result aggregation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats as sp_stats

from simulator.engine.perturbation import PerturbationEngine
from simulator.models.scenario_models import ScenarioDefinition, SimulationResult
from simulator.models.weather import WeatherObservation

_logger = logging.getLogger(__name__)


def _parse_distribution(name: str, params: dict[str, float]) -> tuple[Any, dict[str, Any]]:
    name_lower = name.lower().replace("-", "").replace("_", "")

    if name_lower in ("normal", "norm"):
        mean = params.get("mean", 0.0)
        std = params.get("std", 1.0)
        if std <= 0:
            raise ValueError(f"Standard deviation must be positive, got {std}")
        loc = params.get("loc", mean)
        scale = params.get("scale", std)
        return sp_stats.norm(loc=loc, scale=scale), {}

    if name_lower in ("uniform",):
        low = params.get("low", 0.0)
        high = params.get("high", 1.0)
        if high <= low:
            raise ValueError(f"Uniform high ({high}) must be > low ({low})")
        return sp_stats.uniform(loc=low, scale=high - low), {}

    if name_lower in ("lognormal", "lognorm"):
        mean = params.get("mean", 0.0)
        sigma = params.get("sigma", 0.5)
        if sigma <= 0:
            raise ValueError(f"Log-normal sigma must be positive, got {sigma}")
        return sp_stats.lognorm(s=sigma, scale=np.exp(mean)), {}

    if name_lower in ("triangular", "triang"):
        low = params.get("low", 0.0)
        mode = params.get("mode", 0.5)
        high = params.get("high", 1.0)
        if not (low <= mode <= high):
            raise ValueError(
                f"Triangular must satisfy low ({low}) <= mode ({mode}) <= high ({high})"
            )
        c = (mode - low) / (high - low) if high > low else 0.5
        return sp_stats.triang(c=c, loc=low, scale=high - low), {}

    raise ValueError(
        f"Unknown distribution: '{name}'. Valid: normal, uniform, lognormal, triangular"
    )


@dataclass
class MonteCarloResult:
    n_samples: int
    parameter_distributions: dict[str, dict[str, float]]
    results: list[SimulationResult]
    summary: dict[str, dict[str, float]] = field(default_factory=dict)
    confidence_intervals: dict[str, dict[str, float]] = field(default_factory=dict)
    sensitivity: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.n_samples <= 0:
            raise ValueError(f"n_samples must be positive, got {self.n_samples}")
        if len(self.results) != self.n_samples:
            raise ValueError(
                f"Number of results ({len(self.results)}) must match n_samples ({self.n_samples})"
            )


class MonteCarloEngine:
    def __init__(
        self,
        perturbation_engine: PerturbationEngine,
        n_samples: int = 1000,
        random_seed: int | None = None,
    ) -> None:
        if n_samples <= 0:
            raise ValueError(f"n_samples must be positive, got {n_samples}")
        self._perturbation = perturbation_engine
        self._n_samples = n_samples
        self._rng = np.random.default_rng(random_seed)
        _logger.debug(
            "MonteCarloEngine initialized (n_samples=%d, seed=%s)", n_samples, random_seed
        )

    @property
    def n_samples(self) -> int:
        return self._n_samples

    async def run_monte_carlo(
        self,
        base_data: list[WeatherObservation],
        scenario_template: ScenarioDefinition,
        parameter_distributions: dict[str, dict[str, float]],
    ) -> MonteCarloResult:
        if not base_data:
            raise ValueError("Cannot run Monte Carlo on empty base data")
        if not parameter_distributions:
            raise ValueError("Must provide at least one parameter distribution")

        _logger.info(
            "Running Monte Carlo simulation: %d samples, %d parameters",
            self._n_samples,
            len(parameter_distributions),
        )

        results: list[SimulationResult] = []

        for i in range(self._n_samples):
            sampled_params = self.sample_parameters(parameter_distributions)
            scenario_variant = self._build_scenario(scenario_template, sampled_params)
            perturbed = await self._simulate_single(base_data, scenario_variant, i, sampled_params)
            results.append(perturbed)

        summary = self._compute_summary(results)
        confidence_intervals = self.compute_confidence_intervals(results)
        sensitivity = self.sensitivity_analysis(results, list(parameter_distributions.keys()))

        return MonteCarloResult(
            n_samples=self._n_samples,
            parameter_distributions=parameter_distributions,
            results=results,
            summary=summary,
            confidence_intervals=confidence_intervals,
            sensitivity=sensitivity,
        )

    def sample_parameters(
        self,
        distributions: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        samples: dict[str, float] = {}
        for param_name, dist_spec in distributions.items():
            raw_dist_name = dist_spec.get("distribution", "normal")
            dist_name = str(raw_dist_name) if not isinstance(raw_dist_name, str) else raw_dist_name
            param_spec = {k: v for k, v in dist_spec.items() if k != "distribution"}
            dist, _ = _parse_distribution(dist_name, param_spec)
            sampled = float(dist.rvs(random_state=self._rng))
            samples[param_name] = sampled
        return samples

    def compute_confidence_intervals(
        self,
        results: list[SimulationResult],
        confidence: float = 0.95,
    ) -> dict[str, dict[str, float]]:
        alpha = 1.0 - confidence
        lower_pct = (alpha / 2.0) * 100
        upper_pct = (1.0 - alpha / 2.0) * 100

        cis: dict[str, dict[str, float]] = {}

        if not results:
            return cis

        var_values: dict[str, list[float]] = {}
        for result in results:
            summary_stats = result.simulated.get("summary_statistics", {})
            for var_name, stats_dict in summary_stats.items():
                mean_val = stats_dict.get("mean", 0.0)
                if var_name not in var_values:
                    var_values[var_name] = []
                var_values[var_name].append(mean_val)

        for var_name, values in var_values.items():
            arr = np.array(values, dtype=np.float64)
            cis[var_name] = {
                "lower": float(np.percentile(arr, lower_pct)),
                "upper": float(np.percentile(arr, upper_pct)),
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "p5": float(np.percentile(arr, 5)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
                "p95": float(np.percentile(arr, 95)),
            }

        return cis

    def sensitivity_analysis(
        self,
        results: list[SimulationResult],
        parameters: list[str],
    ) -> dict[str, float]:
        if not results or not parameters:
            return {}

        output_values: list[float] = []
        for result in results:
            summary_stats = result.simulated.get("summary_statistics", {})
            temp_stats = summary_stats.get("temperature_2m", {})
            output_values.append(temp_stats.get("mean", 0.0))

        output_arr = np.array(output_values, dtype=np.float64)
        output_var = float(np.var(output_arr))

        if output_var == 0.0 or len(parameters) == 0:
            return {p: 0.0 for p in parameters}

        has_samples = all(
            isinstance(r.simulated.get("sampled_params"), dict) for r in results
        )
        if has_samples:
            raw_scores: dict[str, float] = {}
            for p in parameters:
                xs = np.array(
                    [float(r.simulated["sampled_params"].get(p, 0.0)) for r in results],
                    dtype=np.float64,
                )
                if float(np.var(xs)) == 0.0:
                    raw_scores[p] = 0.0
                    continue
                corr = float(np.corrcoef(xs, output_arr)[0, 1])
                raw_scores[p] = abs(corr) if np.isfinite(corr) else 0.0
            total = sum(raw_scores.values())
            if total > 0:
                return {k: v / total for k, v in raw_scores.items()}
            return {p: 1.0 / len(parameters) for p in parameters}

        equal_importance = 1.0 / len(parameters)
        return {p: equal_importance for p in parameters}

    async def _simulate_single(
        self,
        base_data: list[WeatherObservation],
        scenario: ScenarioDefinition,
        sample_index: int,
        sampled_params: dict[str, float] | None = None,
    ) -> SimulationResult:
        import time
        from datetime import UTC, datetime

        start_ms = time.perf_counter()

        perturbed = self._perturbation.apply_perturbation(base_data, scenario)

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
                "p5": float(np.percentile(arr, 5)),
                "p50": float(np.percentile(arr, 50)),
                "p95": float(np.percentile(arr, 95)),
            }

        end_ms = time.perf_counter()
        duration_ms = (end_ms - start_ms) * 1000

        baseline_dict = {
            "location_id": base_data[0].location_id if base_data else "unknown",
            "data_source": "monte_carlo_baseline",
        }

        simulated_dict = {
            "data_source": "monte_carlo",
            "scenario_id": scenario.scenario_id,
            "sample_index": sample_index,
            "time_series": time_series,
            "time_steps": [t.isoformat() for t in time_steps],
            "summary_statistics": summary_statistics,
            "sampled_params": dict(sampled_params or {}),
        }

        deltas = {}
        if base_data and perturbed:
            for var_name, values in time_series.items():
                base_arr = np.array(
                    [getattr(o, var_name, 0.0) for o in base_data], dtype=np.float64
                )
                pert_arr = np.array(values, dtype=np.float64)
                deltas[var_name] = float(np.mean(pert_arr - base_arr))

        return SimulationResult(
            location_id=scenario.parameters.get(
                "location_id", base_data[0].location_id if base_data else "unknown"
            ),
            scenario_id=scenario.scenario_id,
            timestamp=datetime.now(UTC).isoformat(),
            baseline=baseline_dict,
            simulated=simulated_dict,
            deltas=deltas,
            duration_ms=round(duration_ms, 2),
            success=True,
        )

    @staticmethod
    def _build_scenario(
        template: ScenarioDefinition,
        sampled_params: dict[str, float],
    ) -> ScenarioDefinition:
        custom_params: dict[str, float | int | str] = dict(template.parameters)

        temp_delta = custom_params.get("temperature_delta")
        rain_mult = custom_params.get("rainfall_multiplier")
        humid_delta = custom_params.get("humidity_delta")
        wind_delta = custom_params.get("wind_speed_delta")
        press_delta = custom_params.get("pressure_delta")

        for param_name, value in sampled_params.items():
            mapped = param_name
            if param_name in ("temperature_2m", "temperature", "max_temp"):
                mapped = "temperature_delta"
            elif param_name in ("precipitation_mm", "rainfall"):
                mapped = "rainfall_multiplier"
            elif param_name == "rainfall_change_pct":
                rain_mult = 1.0 + (value / 100.0)
                continue
            if mapped == "temperature_delta":
                temp_delta = value
            elif mapped == "rainfall_multiplier":
                rain_mult = value
            elif mapped == "humidity_delta":
                humid_delta = value
            elif mapped == "wind_speed_delta":
                wind_delta = value
            elif mapped == "pressure_delta":
                press_delta = value
            else:
                custom_params[param_name] = value

        merged_params = dict(custom_params)
        if temp_delta is not None:
            merged_params["temperature_delta"] = temp_delta
        if rain_mult is not None:
            merged_params["rainfall_multiplier"] = rain_mult
        if humid_delta is not None:
            merged_params["humidity_delta"] = humid_delta
        if wind_delta is not None:
            merged_params["wind_speed_delta"] = wind_delta
        if press_delta is not None:
            merged_params["pressure_delta"] = press_delta

        return ScenarioDefinition(
            scenario_id=template.scenario_id,
            name=f"{template.name} (MC sample)",
            description=f"Monte Carlo sample of: {template.description}",
            scenario_type=template.scenario_type,
            parameters=merged_params,
        )

    @staticmethod
    def _compute_summary(results: list[SimulationResult]) -> dict[str, dict[str, float]]:
        variable_values: dict[str, list[float]] = {}

        for result in results:
            summary_stats = result.simulated.get("summary_statistics", {})
            for var_name, stats in summary_stats.items():
                mean_val = stats.get("mean", 0.0)
                if var_name not in variable_values:
                    variable_values[var_name] = []
                variable_values[var_name].append(mean_val)

        summary: dict[str, dict[str, float]] = {}
        for var_name, values in variable_values.items():
            arr = np.array(values, dtype=np.float64)
            summary[var_name] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "p5": float(np.percentile(arr, 5)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
                "p95": float(np.percentile(arr, 95)),
            }

        return summary


__all__ = [
    "MonteCarloEngine",
    "MonteCarloResult",
]
