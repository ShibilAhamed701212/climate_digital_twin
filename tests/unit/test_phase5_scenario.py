"""Phase 5 — canonical Counterfactual/What-If engine, models, and store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from climatedt.scenario.engine import (
    ZERO_BASELINE_PERCENT_MSG,
    ScenarioEngine,
)
from climatedt.scenario.models import (
    SCENARIO_AUTHENTICITY,
    ScenarioDefinition,
    ScenarioIntervention,
    compute_result_id,
    new_scenario_id,
)
from climatedt.scenario.store import ScenarioStore
from simulator.models.twin_state import TwinState


def make_baseline(**overrides: Any) -> TwinState:
    base: dict[str, Any] = dict(
        entity_id="KA-BLR-001",
        timestamp=datetime(2026, 7, 30, 14, 34, tzinfo=UTC),
        temperature_2m=22.1,
        precipitation_mm=0.0,
        humidity_pct=88.0,
        pressure_hpa=907.5,
        wind_speed_10m=16.6,
        wind_direction_10m=220.0,
        solar_radiation=100.0,
        cloud_cover_pct=60.0,
        soil_moisture=0.207,
        data_source="open_meteo",
        quality_flag="validated",
        authenticity="REAL",
    )
    base.update(overrides)
    return TwinState(**base)


def make_definition(**overrides: Any) -> ScenarioDefinition:
    base: dict[str, Any] = dict(
        scenario_id="sc_001",
        name="+3C Warming",
        description="test",
        scenario_type="temperature",
        location_id="KA-BLR-001",
        interventions=[ScenarioIntervention("temperature_2m", "ADD", 3.0)],
        duration_days=7,
    )
    base.update(overrides)
    return ScenarioDefinition(**base)


class TestScenarioEngine:
    def test_add(self):
        result = ScenarioEngine().apply(
            make_baseline(), [ScenarioIntervention("temperature_2m", "ADD", 3.0)]
        )
        assert result.state.temperature_2m == 25.1
        assert result.deltas["temperature_2m"] == 3.0
        assert result.state.authenticity == SCENARIO_AUTHENTICITY

    def test_subtract(self):
        result = ScenarioEngine().apply(
            make_baseline(), [ScenarioIntervention("temperature_2m", "SUBTRACT", 2.0)]
        )
        assert result.state.temperature_2m == 20.1

    def test_multiply(self):
        result = ScenarioEngine().apply(
            make_baseline(),
            [ScenarioIntervention("precipitation_mm", "MULTIPLY", 1.5)],
        )
        assert result.state.precipitation_mm == 0.0

    def test_set(self):
        result = ScenarioEngine().apply(
            make_baseline(), [ScenarioIntervention("precipitation_mm", "SET", 50.0)]
        )
        assert result.state.precipitation_mm == 50.0
        assert result.deltas["precipitation_mm"] == 50.0

    def test_percent_change(self):
        result = ScenarioEngine().apply(
            make_baseline(temperature_2m=20.0),
            [ScenarioIntervention("temperature_2m", "PERCENT_CHANGE", 10.0)],
        )
        assert result.state.temperature_2m == 22.0

    def test_percent_change_zero_baseline_rejected(self):
        with pytest.raises(ValueError, match=ZERO_BASELINE_PERCENT_MSG):
            ScenarioEngine().apply(
                make_baseline(),
                [ScenarioIntervention("precipitation_mm", "PERCENT_CHANGE", 50.0)],
            )

    def test_rounding_to_two_decimals(self):
        result = ScenarioEngine().apply(
            make_baseline(temperature_2m=22.137),
            [ScenarioIntervention("temperature_2m", "ADD", 3.0)],
        )
        assert result.state.temperature_2m == 25.14

    def test_bounds_rejected_not_clamped(self):
        with pytest.raises(ValueError, match="physical minimum"):
            ScenarioEngine().apply(
                make_baseline(cloud_cover_pct=5.0),
                [ScenarioIntervention("cloud_cover_pct", "SUBTRACT", 10.0)],
            )
        with pytest.raises(ValueError, match="physical maximum"):
            ScenarioEngine().apply(
                make_baseline(humidity_pct=95.0),
                [ScenarioIntervention("humidity_pct", "ADD", 10.0)],
            )

    def test_non_real_baseline_rejected(self):
        with pytest.raises(ValueError, match="REAL"):
            ScenarioEngine().apply(
                make_baseline(authenticity="SYNTHETIC"),
                [ScenarioIntervention("temperature_2m", "ADD", 1.0)],
            )

    def test_deterministic(self):
        engine = ScenarioEngine()
        a = engine.apply(make_baseline(), [ScenarioIntervention("temperature_2m", "ADD", 3.0)])
        b = engine.apply(make_baseline(), [ScenarioIntervention("temperature_2m", "ADD", 3.0)])
        assert a.state == b.state
        assert a.applied_values == b.applied_values
        assert a.deltas == b.deltas

    def test_output_never_real(self):
        result = ScenarioEngine().apply(
            make_baseline(), [ScenarioIntervention("temperature_2m", "ADD", 3.0)]
        )
        assert result.state.authenticity == SCENARIO_AUTHENTICITY
        assert result.state.data_source == "scenario"
        assert result.state.metadata["baseline_authenticity"] == "REAL"

    def test_unknown_variable_rejected(self):
        with pytest.raises(ValueError, match="Unknown scenario variable"):
            ScenarioIntervention("bogus", "ADD", 1.0)

    def test_unknown_operation_rejected(self):
        with pytest.raises(ValueError, match="Unknown operation"):
            ScenarioIntervention("temperature_2m", "DOUBLE", 1.0)

    def test_unit_mismatch_rejected(self):
        with pytest.raises(ValueError, match="does not match canonical unit"):
            ScenarioIntervention("temperature_2m", "ADD", 1.0, unit="mm")


class TestResultIdentity:
    def test_stable_for_same_inputs(self):
        d = make_definition()
        a = compute_result_id(d, "v000001", "2026-07-30T14:34:00Z")
        b = compute_result_id(d, "v000001", "2026-07-30T14:34:00Z")
        assert a == b
        assert a.startswith("scn_")

    def test_changes_with_intervention(self):
        d1 = make_definition()
        d2 = make_definition(interventions=[ScenarioIntervention("temperature_2m", "ADD", 4.0)])
        assert compute_result_id(d1, "v1", "t") != compute_result_id(d2, "v1", "t")

    def test_changes_with_twin_version(self):
        d = make_definition()
        assert compute_result_id(d, "v000001", "t") != compute_result_id(d, "v000002", "t")

    def test_new_scenario_id_unique(self):
        assert new_scenario_id().startswith("scenario_")
        assert new_scenario_id() != new_scenario_id()


class TestScenarioStore:
    def test_round_trip(self, tmp_path):
        store = ScenarioStore(tmp_path)
        d = make_definition()
        store.save_definition(d)
        loaded = store.get_definition("sc_001")
        assert loaded is not None
        assert loaded.scenario_id == "sc_001"
        assert (tmp_path / "definitions.jsonl").exists()

    def test_restart_recovery(self, tmp_path):
        store = ScenarioStore(tmp_path)
        store.save_definition(make_definition())
        store.save_result = store.save_result  # no-op reference to satisfy linters

        store2 = ScenarioStore(tmp_path)
        assert store2.get_definition("sc_001") is not None

    def test_save_forces_scenario_authenticity(self, tmp_path):
        store = ScenarioStore(tmp_path)
        store.save_definition(make_definition(authenticity="REAL"))
        loaded = store.get_definition("sc_001")
        assert loaded is not None
        assert loaded.authenticity == SCENARIO_AUTHENTICITY

    def test_never_touches_unrelated_stores(self, tmp_path):
        store = ScenarioStore(tmp_path)
        store.save_definition(make_definition())
        assert not (tmp_path / "observations.jsonl").exists()
        assert not (tmp_path / "alerts.jsonl").exists()
        files = {p.name for p in tmp_path.iterdir()}
        assert files == {"definitions.jsonl"}
