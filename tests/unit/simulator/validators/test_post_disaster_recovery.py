from __future__ import annotations

from simulator.validators.scenario_validator import validate_scenario_parameters


def test_post_disaster_requires_assessment_id(monkeypatch) -> None:
    from simulator.validators import scenario_validator as sv

    sv._SCENARIO_CONFIG = {
        "scenarios": {"extreme_events": {"enabled": True, "types": ["flood"]}},
        "validation": {},
    }
    errors = validate_scenario_parameters("post_disaster_recovery", {})
    assert errors
    ok = validate_scenario_parameters("post_disaster_recovery", {"assessment_id": "01ABC"})
    assert ok == []
    sv._SCENARIO_CONFIG = None
