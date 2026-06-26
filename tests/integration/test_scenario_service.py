"""Integration tests for the Scenario Service with the Digital Twin."""

from __future__ import annotations

import pytest


@pytest.fixture
def twin_engine():
    """Create a DigitalTwinEngine for testing."""
    from simulator.engine.twin_engine import DigitalTwinEngine

    engine = DigitalTwinEngine(
        config_path="simulator/configs/twin_config.yaml",
        store_dir="data/test_twin_store",
    )
    return engine


class TestScenarioServiceIntegration:
    """Integration tests for ScenarioService with DigitalTwinEngine."""

    @pytest.fixture
    def service(self, twin_engine):
        from simulator.engine.scenario_engine import ScenarioEngine
        from simulator.services.scenario_service import ScenarioService

        return ScenarioService(twin_engine, ScenarioEngine())

    def test_create_and_list_scenario(self, service):
        from simulator.scenarios.scenario_builder import list_preset_scenarios

        s = service.create_scenario(
            scenario_id="int_test_001",
            name="Integration Test",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        assert s.scenario_id == "int_test_001"

        all_scenarios = service.list_scenarios()
        preset_count = len(list_preset_scenarios())
        assert len(all_scenarios) == preset_count + 1

    def test_validate_scenario(self, service):
        errors = service.validate_scenario("temperature", {"temperature_delta": 2.0})
        assert errors == []

        errors = service.validate_scenario("temperature", {"temperature_delta": 100.0})
        assert len(errors) > 0

    def test_run_simulation_preset(self, twin_engine, service):
        entity = twin_engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        entity = entity.update_state(rainfall=100.0, max_temp=32.0, min_temp=20.0)
        twin_engine.ingest_observation(entity)

        run = service.run_simulation("temp_plus_2", location_ids=["KA-BLR-001"])
        assert run.status == "completed"
        assert run.location_count == 1
        assert len(run.results) == 1
        assert run.results[0].success
        assert abs(run.results[0].deltas.get("max_temp", 0) - 2.0) < 0.1

    def test_run_simulation_no_location_fallback(self, twin_engine, service):
        entity = twin_engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        twin_engine.ingest_observation(entity)
        entity2 = twin_engine.create_entity("KA-MYS-001", 12.30, 76.65, "Mysuru")
        twin_engine.ingest_observation(entity2)

        run = service.run_simulation("rain_plus_40")
        assert run.status == "completed"
        assert run.location_count >= 2

    def test_compare_with_baseline(self, twin_engine, service):
        entity = twin_engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        twin_engine.ingest_observation(entity)

        run = service.run_simulation("temp_plus_1", location_ids=["KA-BLR-001"])
        comparisons = service.compare_with_baseline(run)
        assert len(comparisons) == 1
        assert comparisons[0]["location_id"] == "KA-BLR-001"

    def test_delete_scenario(self, service):
        service.create_scenario(
            scenario_id="delete_test",
            name="To Delete",
            description="",
            scenario_type="temperature",
            parameters={"temperature_delta": 1.0},
        )
        assert service.delete_scenario("delete_test") is True
        assert service.delete_scenario("nonexistent") is False

    def test_event_publishing(self, twin_engine, service):
        events_before = len(twin_engine.event_bus.get_event_history())

        service.create_scenario(
            scenario_id="event_test",
            name="Event Test",
            description="",
            scenario_type="rainfall",
            parameters={"rainfall_change_pct": 10.0},
        )

        events_after = len(twin_engine.event_bus.get_event_history())
        assert events_after > events_before

    def test_simulation_events(self, twin_engine, service):
        entity = twin_engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        twin_engine.ingest_observation(entity)

        before_count = len(twin_engine.event_bus.get_event_history())
        service.run_simulation("temp_plus_1", location_ids=["KA-BLR-001"])
        after_count = len(twin_engine.event_bus.get_event_history())
        assert after_count - before_count >= 2

    def test_full_lifecycle(self, twin_engine, service):
        entity = twin_engine.create_entity("KA-BLR-001", 12.97, 77.59, "Bengaluru Urban")
        twin_engine.ingest_observation(entity)

        s = service.create_scenario(
            scenario_id="lifecycle_test",
            name="Lifecycle",
            description="Full lifecycle test",
            scenario_type="temperature",
            parameters={"temperature_delta": 3.0},
        )
        run = service.run_simulation("lifecycle_test", location_ids=["KA-BLR-001"])
        comparisons = service.compare_with_baseline(run)

        assert s is not None
        assert run.status == "completed"
        assert len(comparisons) == 1
        assert service.delete_scenario("lifecycle_test") is True
