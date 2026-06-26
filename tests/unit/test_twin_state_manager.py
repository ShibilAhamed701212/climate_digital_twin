"""Unit tests for simulator/state_manager/."""

import pytest

from simulator.entities.climate_entity import ClimateEntity
from simulator.state_manager.manager import StateManager, VersionNotFoundError
from simulator.state_manager.version import Version


class TestStateManager:
    @pytest.fixture
    def manager(self) -> StateManager:
        return StateManager()

    @pytest.fixture
    def sample_entity(self) -> ClimateEntity:
        return ClimateEntity(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            district="Bengaluru Urban",
        )

    def test_create_version(self, manager: StateManager, sample_entity: ClimateEntity):
        version = manager.create_version(sample_entity)
        assert version.version_id == 1
        assert version.location_id == "KA-BLR-001"

    def test_version_id_increments(self, manager: StateManager, sample_entity: ClimateEntity):
        v1 = manager.create_version(sample_entity)
        v2 = manager.create_version(sample_entity.update_state(rainfall=10))
        assert v1.version_id == 1
        assert v2.version_id == 2

    def test_get_current(self, manager: StateManager, sample_entity: ClimateEntity):
        manager.create_version(sample_entity)
        current = manager.get_current("KA-BLR-001")
        assert current is not None
        assert current.version_id == 1

    def test_get_current_nonexistent(self, manager: StateManager):
        assert manager.get_current("NONEXISTENT") is None

    def test_get_version(self, manager: StateManager, sample_entity: ClimateEntity):
        created = manager.create_version(sample_entity)
        retrieved = manager.get_version("KA-BLR-001", 1)
        assert retrieved.version_id == created.version_id

    def test_get_version_not_found_raises(self, manager: StateManager):
        with pytest.raises(VersionNotFoundError):
            manager.get_version("KA-BLR-001", 999)

    def test_get_version_history(self, manager: StateManager, sample_entity: ClimateEntity):
        manager.create_version(sample_entity)
        manager.create_version(sample_entity.update_state(rainfall=20))
        history = manager.get_version_history("KA-BLR-001")
        assert len(history) == 2

    def test_rollback_creates_new_version(self, manager: StateManager, sample_entity: ClimateEntity):
        v1 = manager.create_version(sample_entity)
        manager.create_version(sample_entity.update_state(rainfall=50))
        v3 = manager.rollback("KA-BLR-001", 1)
        assert v3.version_id == 3
        assert v3.entity_data["rainfall"] == v1.entity_data["rainfall"]

    def test_rollback_immutability(self, manager: StateManager, sample_entity: ClimateEntity):
        v1 = manager.create_version(sample_entity)
        with pytest.raises(AttributeError):
            v1.entity_data = {"changed": True}  # frozen dataclass prevents attr reassign

    def test_has_location(self, manager: StateManager, sample_entity: ClimateEntity):
        assert not manager.has_location("KA-BLR-001")
        manager.create_version(sample_entity)
        assert manager.has_location("KA-BLR-001")

    def test_get_all_location_ids(self, manager: StateManager):
        e1 = ClimateEntity(location_id="LOC-001", latitude=15.0, longitude=76.0)
        e2 = ClimateEntity(location_id="LOC-002", latitude=16.0, longitude=77.0)
        manager.create_version(e1)
        manager.create_version(e2)
        ids = manager.get_all_location_ids()
        assert "LOC-001" in ids
        assert "LOC-002" in ids

    def test_version_count(self, manager: StateManager, sample_entity: ClimateEntity):
        assert manager.version_count("KA-BLR-001") == 0
        manager.create_version(sample_entity)
        assert manager.version_count("KA-BLR-001") == 1
        manager.create_version(sample_entity.update_state(rainfall=10))
        assert manager.version_count("KA-BLR-001") == 2

    def test_rejects_invalid_entity(self, manager: StateManager):
        invalid = ClimateEntity(location_id="", latitude=200, longitude=77.59)
        with pytest.raises(ValueError):
            manager.create_version(invalid)

    def test_version_is_frozen(self):
        v = Version(version_id=1, location_id="KA-BLR-001", entity_data={"rainfall": 10})
        with pytest.raises(AttributeError):
            v.version_id = 2
