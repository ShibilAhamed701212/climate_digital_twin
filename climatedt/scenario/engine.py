"""Phase 5 — deterministic Counterfactual / What-If Scenario Engine.

Applies ordered arithmetic interventions to an immutable REAL Twin baseline and
returns a perturbed TwinState marked ``authenticity = SCENARIO``.  No random, no
NumPy in the core path.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from simulator.models.twin_state import TwinState

from climatedt.scenario.models import (
    SCENARIO_AUTHENTICITY,
    VARIABLE_BOUNDS,
    VARIABLE_UNITS,
    ScenarioIntervention,
)

ZERO_BASELINE_PERCENT_MSG = (
    "PERCENT_CHANGE has no effect on a zero baseline; "
    "use ADD or SET for an absolute hypothetical rainfall scenario."
)


def _is_finite(x: float) -> bool:
    return x == x and x not in (float("inf"), float("-inf"))


def apply_operation(current: float, iv: ScenarioIntervention) -> float:
    if iv.operation == "ADD":
        return current + iv.value
    if iv.operation == "SUBTRACT":
        return current - iv.value
    if iv.operation == "MULTIPLY":
        return current * iv.value
    if iv.operation == "SET":
        return iv.value
    if iv.operation == "PERCENT_CHANGE":
        if current == 0.0:
            raise ValueError(
                f"{ZERO_BASELINE_PERCENT_MSG} (variable='{iv.variable}', baseline={current})"
            )
        return current * (1.0 + iv.value / 100.0)
    raise ValueError(f"Unknown operation '{iv.operation}'")


def _check_bounds(variable: str, value: float) -> None:
    lo, hi = VARIABLE_BOUNDS[variable]
    if lo is not None and value < lo:
        raise ValueError(
            f"Intervention on '{variable}' produces {value} which is below the "
            f"physical minimum {lo}{VARIABLE_UNITS[variable]}"
        )
    if hi is not None and value >= hi and variable == "wind_direction_10m":
        raise ValueError(
            f"Intervention on '{variable}' produces {value}° which must be in [0, 360)"
        )
    if hi is not None and variable != "wind_direction_10m" and value > hi:
        raise ValueError(
            f"Intervention on '{variable}' produces {value} which is above the "
            f"physical maximum {hi}{VARIABLE_UNITS[variable]}"
        )


@dataclass
class EngineResult:
    state: TwinState
    applied_values: dict[str, float]
    deltas: dict[str, float]


class ScenarioEngine:
    """Deterministic counterfactual engine over TwinState baselines."""

    def apply(
        self,
        baseline: TwinState,
        interventions: list[ScenarioIntervention],
        scenario_id: str = "scenario",
        description: str = "",
    ) -> EngineResult:
        if baseline.authenticity.upper() != "REAL":
            raise ValueError(
                "Scenario baselines must be authoritative REAL twin state; "
                f"got authenticity={baseline.authenticity}"
            )

        values: dict[str, float | None] = {}
        deltas: dict[str, float] = {}
        for variable in VARIABLE_UNITS:
            base = getattr(baseline, variable, None)
            values[variable] = base
            deltas[variable] = 0.0

        for iv in interventions:
            current = values.get(iv.variable)
            if current is None:
                raise ValueError(
                    f"Baseline twin has no value for '{iv.variable}' — cannot apply "
                    f"{iv.operation} intervention"
                )
            if not _is_finite(current):
                raise ValueError(
                    f"Baseline twin value for '{iv.variable}' is not finite ({current})"
                )
            applied = apply_operation(float(current), iv)
            applied = round(applied, 2)
            if not _is_finite(applied):
                raise ValueError(f"Intervention on '{iv.variable}' produces a non-finite value")
            _check_bounds(iv.variable, applied)
            values[iv.variable] = applied
            deltas[iv.variable] = round(applied - float(current), 2)

        metadata = dict(baseline.metadata or {})
        metadata.update(
            {
                "scenario_id": scenario_id,
                "scenario_description": description,
                "baseline_authenticity": baseline.authenticity.upper(),
            }
        )

        kwargs: dict[str, Any] = {
            var: values[var] for var in VARIABLE_UNITS if getattr(baseline, var, None) is not None
        }
        kwargs.update(
            {
                "data_source": "scenario",
                "quality_flag": "simulated",
                "authenticity": SCENARIO_AUTHENTICITY,
                "metadata": metadata,
            }
        )
        state = replace(baseline, **kwargs)
        return EngineResult(
            state=state,
            applied_values={k: v for k, v in values.items() if v is not None},
            deltas=deltas,
        )
