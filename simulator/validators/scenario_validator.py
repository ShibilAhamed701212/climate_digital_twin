"""Input bounds and constraint validation for scenario parameters."""

from __future__ import annotations

from typing import Any

import yaml

_SCENARIO_CONFIG: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    global _SCENARIO_CONFIG
    if _SCENARIO_CONFIG is None:
        with open("simulator/configs/scenario.yaml") as f:
            _SCENARIO_CONFIG = yaml.safe_load(f)
    return _SCENARIO_CONFIG


class ScenarioValidationError(ValueError):
    """Raised when scenario parameters fail validation."""


def validate_scenario_parameters(
    scenario_type: str,
    parameters: dict[str, Any],
) -> list[str]:
    """Validate scenario parameters against configured constraints.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    cfg = _load_config()

    if scenario_type == "temperature":
        errors.extend(_validate_temperature(parameters, cfg))
    elif scenario_type == "rainfall":
        errors.extend(_validate_rainfall(parameters, cfg))
    elif scenario_type == "monsoon":
        errors.extend(_validate_monsoon(parameters, cfg))
    elif scenario_type == "extreme_event":
        errors.extend(_validate_extreme_event(parameters, cfg))
    elif scenario_type == "combined":
        errors.extend(_validate_combined(parameters, cfg))
    else:
        errors.append(f"Unsupported scenario type: {scenario_type}")

    return errors


def _validate_temperature(
    params: dict[str, Any], cfg: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    temp_cfg = cfg.get("scenarios", {}).get("temperature", {})
    delta = _get_float(params, "temperature_delta")
    if delta is None:
        errors.append("temperature_delta is required")
        return errors
    min_d = temp_cfg.get("min_delta", -5.0)
    max_d = temp_cfg.get("max_delta", 5.0)
    if delta < min_d or delta > max_d:
        errors.append(
            f"temperature_delta {delta} out of range [{min_d}, {max_d}]"
        )
    return errors


def _validate_rainfall(
    params: dict[str, Any], cfg: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    rain_cfg = cfg.get("scenarios", {}).get("rainfall", {})
    pct = _get_float(params, "rainfall_change_pct")
    if pct is None:
        errors.append("rainfall_change_pct is required")
        return errors
    min_pct = rain_cfg.get("min_percent_change", -100.0)
    max_pct = rain_cfg.get("max_percent_change", 500.0)
    if pct < min_pct or pct > max_pct:
        errors.append(
            f"rainfall_change_pct {pct} out of range [{min_pct}, {max_pct}]"
        )
    return errors


def _validate_monsoon(
    params: dict[str, Any], cfg: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    mon_cfg = cfg.get("scenarios", {}).get("monsoon", {})
    delay = _get_int(params, "delay_days")
    if delay is None:
        errors.append("delay_days is required")
        return errors
    max_delay = mon_cfg.get("max_delay_days", 30)
    max_advance = mon_cfg.get("max_advance_days", 15)
    if delay < -max_advance or delay > max_delay:
        errors.append(
            f"delay_days {delay} out of range [{-max_advance}, {max_delay}]"
        )
    intensity = _get_float(params, "intensity_reduction_pct")
    if intensity is not None:
        ir = mon_cfg.get("intensity_reduction_range", [0, 50])
        if intensity < ir[0] or intensity > ir[1]:
            errors.append(
                f"intensity_reduction_pct {intensity} out of range [{ir[0]}, {ir[1]}]"
            )
    return errors


def _validate_extreme_event(
    params: dict[str, Any], cfg: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    event_cfg = cfg.get("scenarios", {}).get("extreme_events", {})
    if not event_cfg.get("enabled", True):
        errors.append("Extreme events are disabled")
        return errors
    event_type = params.get("event_type", "")
    valid_types = event_cfg.get("types", [])
    if event_type not in valid_types:
        errors.append(
            f"Unsupported extreme event type: {event_type}. "
            f"Valid: {valid_types}"
        )
    return errors


def _validate_combined(
    params: dict[str, Any], cfg: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    val_cfg = cfg.get("validation", {})
    max_combined = val_cfg.get("max_combined_scenarios", 5)
    sub_scenarios = params.get("scenarios", [])
    if not isinstance(sub_scenarios, list):
        errors.append("combined scenario requires a list of sub-scenarios")
        return errors
    if len(sub_scenarios) > max_combined:
        errors.append(
            f"Too many combined scenarios: {len(sub_scenarios)} > {max_combined}"
        )
    for i, sub in enumerate(sub_scenarios):
        if not isinstance(sub, dict):
            errors.append(f"Sub-scenario {i} is not a dict")
            continue
        st = sub.get("scenario_type", "")
        sp = sub.get("parameters", {})
        sub_errors = validate_scenario_parameters(st, sp)
        errors.extend(f"sub[{i}]: {e}" for e in sub_errors)
    return errors


def _get_float(params: dict[str, Any], key: str) -> float | None:
    val = params.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get_int(params: dict[str, Any], key: str) -> int | None:
    val = params.get(key)
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
