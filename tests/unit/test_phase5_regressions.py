"""Phase 5 — isolation regression tests.

Five mandatory regressions from the Phase 5 spec, plus the defense-in-depth
checks that scenario/synthetic state can never reach authoritative persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from climatedt.scenario.service import ScenarioService
from risk.evaluation.twin_adapter import extract_twin_inputs
from simulator.entities.climate_entity import ClimateEntity
from simulator.models.twin_state import TwinState


def make_twin_state(**overrides: Any) -> TwinState:
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


SERVICE_SRC = Path("climatedt/scenario/service.py").read_text(encoding="utf-8")


class TestRegression1NoHardcodedFallback:
    def test_no_fake_weather_fallback_in_service(self):
        assert "refusing to substitute hardcoded weather" in SERVICE_SRC
        assert '"max_temp": 30' not in SERVICE_SRC
        assert '"min_temp": 20' not in SERVICE_SRC
        assert '"rainfall": 50' not in SERVICE_SRC


class TestRegression2ScenarioIdNeverLocationId:
    @pytest.mark.asyncio
    async def test_twin_manager_receives_location_id(self):
        captured: dict[str, Any] = {}

        class FakeTwin:
            async def get_current_state(self, location_id: str) -> TwinState:
                captured["location_id"] = location_id
                return make_twin_state()

        svc = ScenarioService(twin_manager=FakeTwin())
        from climatedt.scenario.models import ScenarioDefinition, ScenarioIntervention

        scenario = ScenarioDefinition(
            scenario_id="LOC-B",  # deliberately looks like a location id
            name="trap",
            description="",
            scenario_type="temperature",
            location_id="LOC-A",  # the real location
            interventions=[ScenarioIntervention("temperature_2m", "ADD", 1.0)],
        )
        result = await svc.run_scenario(scenario)
        assert captured["location_id"] == "LOC-A"
        assert result.location_id == "LOC-A"

    @pytest.mark.asyncio
    async def test_missing_twin_refuses(self):
        class FakeTwin:
            async def get_current_state(self, _location_id: str) -> None:
                raise ValueError("no state")

        svc = ScenarioService(twin_manager=FakeTwin())
        from climatedt.scenario.models import ScenarioDefinition, ScenarioIntervention

        scenario = ScenarioDefinition(
            scenario_id="s1",
            name="",
            description="",
            scenario_type="temperature",
            location_id="KA-BLR-001",
            interventions=[ScenarioIntervention("temperature_2m", "ADD", 1.0)],
        )
        with pytest.raises(ValueError, match="refusing to substitute"):
            await svc.run_scenario(scenario)


class TestRegression3LegacyDemoNeverPersistsToRealTwin:
    def test_demo_run_simulation_does_not_write_scenario(self):
        from simulator.services.scenario_service import ScenarioService as DemoService

        apply_scenario = MagicMock()
        event_bus = MagicMock()
        twin = MagicMock()
        twin.event_bus = event_bus
        twin.get_current_state.return_value = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bengaluru",
            timestamp="2026-07-30T14:34:00Z",
            rainfall=0.0,
            max_temp=22.1,
            min_temp=18.0,
        ).serialize()
        twin.service.state_manager.get_all_location_ids.return_value = ["KA-BLR-001"]
        twin.apply_scenario = apply_scenario

        demo = DemoService(twin_engine=twin)
        run = demo.run_simulation("temp_plus_2")
        assert run is not None
        apply_scenario.assert_not_called()


class TestRegression4ScenarioHazardNeverAlerts:
    @pytest.mark.asyncio
    async def test_assess_scenario_creates_no_alerts(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        evaluator._alert_store = MagicMock()
        evaluator._alert_policy = MagicMock()
        baseline = make_twin_state()
        assessment = evaluator.assess_scenario(extract_twin_inputs(baseline), baseline.entity_id)
        evaluator._alert_store.save.assert_not_called()
        evaluator._alert_policy.evaluate.assert_not_called()
        assert assessment is not None


class TestRegression5DashboardNeverRoutesThrough8002:
    def test_scenario_client_uses_gateway_not_scenario_engine_url(self):
        src = Path("dashboard/services/api_client.py").read_text(encoding="utf-8")
        assert "SCENARIO_ENGINE_URL" not in src


class TestDefenseInDepth:
    def test_authoritative_store_rejects_non_real(self):
        from simulator.repository.versioned_state_store import VersionedStateStore

        store = VersionedStateStore.__new__(VersionedStateStore)
        with pytest.raises(ValueError, match="non-REAL"):
            store.save_state(make_twin_state(authenticity="SCENARIO"))

    def test_twin_service_rejects_scenario_authenticity(self):
        from simulator.services.twin_service import TwinService

        svc = TwinService.__new__(TwinService)
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bengaluru",
            timestamp="2026-07-30T14:34:00Z",
            rainfall=0.0,
            max_temp=22.1,
            min_temp=18.0,
            authenticity="SCENARIO",
        )
        svc._validate_entity = MagicMock(return_value=[])
        with pytest.raises(ValueError, match="Refusing to persist non-REAL"):
            svc.apply_scenario(entity, "sc_001")

    def test_twin_service_accepts_bare_entity(self):
        from simulator.services.twin_service import TwinService

        svc = TwinService.__new__(TwinService)
        svc.state_manager = MagicMock()
        svc.repository = MagicMock()
        svc.event_bus = MagicMock()
        svc.state_manager.create_version.return_value = MagicMock(version_id=1)
        entity = ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bengaluru",
            timestamp="2026-07-30T14:34:00Z",
            rainfall=0.0,
            max_temp=22.1,
            min_temp=18.0,
        )
        svc._validate_entity = MagicMock(return_value=[])
        result = svc.apply_scenario(entity, "sc_001")
        assert result["version_id"] == 1


class TestUpdateStateAuthoritativeSourceGuard:
    @pytest.mark.asyncio
    async def test_update_state_rejects_scenario_source(self):
        from simulator.models.twin_state import StateDelta
        from simulator.state_manager.bhai_state_manager import TwinStateManager

        manager = TwinStateManager.__new__(TwinStateManager)
        delta = StateDelta(
            entity_id="KA-BLR-001",
            from_version_id="",
            to_version_id="",
            delta_temperature=3.0,
        )
        with pytest.raises(ValueError, match="Refusing to persist non-REAL"):
            await manager.update_state("KA-BLR-001", delta, source="scenario")

    @pytest.mark.asyncio
    async def test_update_state_rejects_synthetic_source(self):
        from simulator.models.twin_state import StateDelta
        from simulator.state_manager.bhai_state_manager import TwinStateManager

        manager = TwinStateManager.__new__(TwinStateManager)
        delta = StateDelta(
            entity_id="KA-BLR-001",
            from_version_id="",
            to_version_id="",
            delta_temperature=1.0,
        )
        with pytest.raises(ValueError, match="Refusing to persist non-REAL"):
            await manager.update_state("KA-BLR-001", delta, source="synthetic")

    @pytest.mark.asyncio
    async def test_update_state_accepts_authoritative_source(self):
        from simulator.models.twin_state import StateDelta
        from simulator.state_manager.bhai_state_manager import TwinStateManager

        manager = TwinStateManager.__new__(TwinStateManager)
        manager._store = MagicMock()
        delta = StateDelta(
            entity_id="KA-BLR-001",
            from_version_id="",
            to_version_id="",
            delta_temperature=0.5,
        )
        manager.get_current_state = AsyncMock(return_value=make_twin_state())
        manager._store.save_state.return_value = MagicMock(version_id="v1")
        result = await manager.update_state(
            "KA-BLR-001", delta, source="twin_synchronizer"
        )
        assert result is not None
