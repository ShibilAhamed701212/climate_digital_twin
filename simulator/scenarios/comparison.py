"""Scenario comparison service for analyzing simulation results.

Supports baseline vs scenario comparison, multi-scenario comparison,
statistical significance testing, and report generation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np
from scipy import stats as sp_stats

from simulator.models.scenario_models import SimulationResult

_logger = logging.getLogger(__name__)


@dataclass
class SimulationComparison:
    comparison_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    baseline_result_id: str = ""
    scenario_result_id: str = ""
    location_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    variable_deltas: dict[str, dict[str, float]] = field(default_factory=dict)
    percentage_changes: dict[str, float] = field(default_factory=dict)
    significant_variables: list[str] = field(default_factory=list)
    summary: str = ""


class ScenarioComparison:
    def compare_baseline_scenario(
        self,
        baseline: SimulationResult,
        scenario: SimulationResult,
    ) -> SimulationComparison:
        if baseline.location_id != scenario.location_id:
            raise ValueError(
                f"Location mismatch: baseline='{baseline.location_id}' vs "
                f"scenario='{scenario.location_id}'"
            )

        baseline_ts = baseline.simulated.get("time_series", {})
        scenario_ts = scenario.simulated.get("time_series", {})

        variable_deltas: dict[str, dict[str, float]] = {}
        percentage_changes: dict[str, float] = {}
        significant_variables: list[str] = []

        all_vars = set(baseline_ts.keys()) | set(scenario_ts.keys())

        for var_name in sorted(all_vars):
            base_values = baseline_ts.get(var_name, [])
            scen_values = scenario_ts.get(var_name, [])

            if not base_values or not scen_values:
                continue

            base_arr = np.array(base_values, dtype=np.float64)
            scen_arr = np.array(scen_values, dtype=np.float64)
            deltas = scen_arr - base_arr

            variable_deltas[var_name] = {
                "mean": float(np.mean(deltas)),
                "max": float(np.max(deltas)),
                "min": float(np.min(deltas)),
                "std": float(np.std(deltas)),
                "median": float(np.median(deltas)),
            }

            base_mean = float(np.mean(base_arr))
            if base_mean != 0:
                pct_change = ((float(np.mean(scen_arr)) - base_mean) / abs(base_mean)) * 100.0
            else:
                pct_change = 0.0 if float(np.mean(scen_arr)) == 0 else float("inf")
            percentage_changes[var_name] = pct_change

            if len(base_values) >= 30 and len(scen_values) >= 30:
                try:
                    t_stat, p_value = sp_stats.ttest_ind(base_arr, scen_arr, equal_var=False)
                    if p_value < 0.05:
                        significant_variables.append(var_name)
                except (ValueError, ZeroDivisionError):
                    pass

        return SimulationComparison(
            baseline_result_id=baseline.scenario_id,
            scenario_result_id=scenario.scenario_id,
            location_id=baseline.location_id,
            timestamp=datetime.now(UTC),
            variable_deltas=variable_deltas,
            percentage_changes=percentage_changes,
            significant_variables=significant_variables,
            summary=self._generate_summary_text(
                variable_deltas, percentage_changes, significant_variables
            ),
        )

    def compare_multiple(
        self,
        results: dict[str, SimulationResult],
    ) -> dict[str, SimulationComparison]:
        if len(results) < 2:
            raise ValueError(f"Need at least 2 results for comparison, got {len(results)}")

        keys = list(results.keys())
        baseline = results[keys[0]]
        comparisons: dict[str, SimulationComparison] = {}

        for key in keys[1:]:
            comparison = self.compare_baseline_scenario(baseline, results[key])
            comparisons[f"{keys[0]}_vs_{key}"] = comparison

        return comparisons

    def compute_percentage_changes(
        self,
        baseline: dict[str, float],
        scenario: dict[str, float],
    ) -> dict[str, float]:
        changes: dict[str, float] = {}
        all_keys = set(baseline.keys()) | set(scenario.keys())

        for key in sorted(all_keys):
            base_val = baseline.get(key, 0.0)
            scen_val = scenario.get(key, 0.0)

            if base_val != 0:
                pct = ((scen_val - base_val) / abs(base_val)) * 100.0
            else:
                pct = 0.0 if scen_val == 0 else float("inf")
            changes[key] = pct

        return changes

    def significance_test(
        self,
        baseline: np.ndarray,
        scenario: np.ndarray,
        alpha: float = 0.05,
    ) -> bool:
        if len(baseline) < 2 or len(scenario) < 2:
            return False

        try:
            _, p_value = sp_stats.mannwhitneyu(baseline, scenario, alternative="two-sided")
            return bool(p_value < alpha)
        except ValueError:
            return False

    def generate_comparison_report(
        self,
        comparisons: list[SimulationComparison],
    ) -> dict[str, Any]:
        if not comparisons:
            return {
                "summary": "No comparisons to report.",
                "num_comparisons": 0,
                "key_findings": [],
                "variable_summary": {},
            }

        all_significant: set[str] = set()
        variable_summary: dict[str, dict[str, Any]] = {}

        for comp in comparisons:
            for var_name in comp.significant_variables:
                all_significant.add(var_name)

            for var_name, deltas in comp.variable_deltas.items():
                if var_name not in variable_summary:
                    variable_summary[var_name] = {
                        "mean_deltas": [],
                        "pct_changes": [],
                    }
                variable_summary[var_name]["mean_deltas"].append(deltas.get("mean", 0.0))

            for var_name, pct in comp.percentage_changes.items():
                if var_name in variable_summary:
                    variable_summary[var_name]["pct_changes"].append(pct)

        for _var_name, stats in variable_summary.items():
            if stats["mean_deltas"]:
                arr = np.array(stats["mean_deltas"], dtype=np.float64)
                stats["avg_delta"] = float(np.mean(arr))
                stats["delta_range"] = [float(np.min(arr)), float(np.max(arr))]
            if stats["pct_changes"]:
                arr = np.array(stats["pct_changes"], dtype=np.float64)
                stats["avg_pct_change"] = float(np.mean(arr))

        key_findings: list[str] = []
        for var_name in sorted(all_significant):
            key_findings.append(
                f"Statistically significant change detected in {var_name} (p < 0.05)"
            )

        return {
            "summary": (
                f"Comparison report for {len(comparisons)} scenario comparison(s). "
                f"Found {len(all_significant)} variable(s) with significant changes."
            ),
            "num_comparisons": len(comparisons),
            "key_findings": key_findings,
            "variable_summary": variable_summary,
        }

    @staticmethod
    def _generate_summary_text(
        variable_deltas: dict[str, dict[str, float]],
        percentage_changes: dict[str, float],
        significant_variables: list[str],
    ) -> str:
        parts: list[str] = []

        for var_name in sorted(variable_deltas.keys()):
            deltas = variable_deltas[var_name]
            pct = percentage_changes.get(var_name, 0.0)
            sig = " (significant)" if var_name in significant_variables else ""
            parts.append(
                f"{var_name}: mean delta={deltas['mean']:+.2f}, "
                f"range=[{deltas['min']:+.2f}, {deltas['max']:+.2f}], "
                f"change={pct:+.1f}%{sig}"
            )

        return " | ".join(parts) if parts else "No variable changes detected."


__all__ = [
    "ScenarioComparison",
    "SimulationComparison",
]
