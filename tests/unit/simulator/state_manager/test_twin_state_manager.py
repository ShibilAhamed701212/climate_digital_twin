"""Unit tests for simulator/state_manager/bhai_state_manager.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from simulator.conflict.resolver import ConflictResolver
from simulator.graph.entity_graph import RelationshipType
from simulator.models.twin_state import StateDelta, TwinState, TwinStateVersion
from simulator.models.weather import DataSource, QualityFlag, WeatherObservation
from simulator.reconciliation.engine import ReconciliationResult, StateReconciler
from simulator.repository.versioned_state_store import VersionedStateStore


@pytest.fixture
def mock_store():
    store = MagicMock(spec=VersionedStateStore)
    store._version_index_path = MagicMock()
    store._version_index_path.exists.return_value = True
    return store


@pytest.fixture
def mock_conflict_resolver():
    return MagicMock(spec=ConflictResolver)


@pytest.fixture
def mock_reconciler():
    return MagicMock(spec=StateReconciler)


@pytest.fixture
def mock_graph():
    g = MagicMock()
    g.entity_count.return_value = 0
    return g


@pytest.fixture
def base_twin_state():
    return TwinState(
        entity_id="KA-BLR-001",
        timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        temperature_2m=28.5,
        precipitation_mm=10.0,
        humidity_pct=65.0,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=180.0,
    )


class TestTwinStateManager:
    def test_init_defaults(self):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mgr = TwinStateManager()
        assert mgr.store is not None
        assert mgr.conflict_resolver is not None
        assert mgr.reconciler is not None
        assert mgr.graph is not None

    def test_init_with_dependencies(
        self, mock_store, mock_conflict_resolver, mock_reconciler, mock_graph
    ):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mgr = TwinStateManager(
            store=mock_store,
            conflict_resolver=mock_conflict_resolver,
            reconciler=mock_reconciler,
            graph=mock_graph,
        )
        assert mgr.store is mock_store
        assert mgr.conflict_resolver is mock_conflict_resolver
        assert mgr.reconciler is mock_reconciler
        assert mgr.graph is mock_graph

    @pytest.mark.asyncio
    async def test_get_current_state_found(self, mock_store, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_latest_state.return_value = base_twin_state
        mgr = TwinStateManager(store=mock_store)

        state = await mgr.get_current_state("KA-BLR-001")
        assert state == base_twin_state
        mock_store.get_latest_state.assert_called_once_with("KA-BLR-001")

    @pytest.mark.asyncio
    async def test_get_current_state_not_found(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_latest_state.return_value = None
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="No state found for location 'KA-BLR-001'"):
            await mgr.get_current_state("KA-BLR-001")

    @pytest.mark.asyncio
    async def test_get_state_at_time(self, mock_store, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        ts = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        mock_store.get_state_at_time.return_value = base_twin_state
        mgr = TwinStateManager(store=mock_store)

        state = await mgr.get_state_at_time("KA-BLR-001", ts)
        assert state == base_twin_state
        mock_store.get_state_at_time.assert_called_once_with("KA-BLR-001", ts)

    @pytest.mark.asyncio
    async def test_get_state_at_time_none(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        ts = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        mock_store.get_state_at_time.return_value = None
        mgr = TwinStateManager(store=mock_store)

        state = await mgr.get_state_at_time("KA-BLR-001", ts)
        assert state is None

    @pytest.mark.asyncio
    async def test_get_state_version_found(self, mock_store, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.return_value = base_twin_state
        mgr = TwinStateManager(store=mock_store)

        state = await mgr.get_state_version("KA-BLR-001", 2)
        assert state == base_twin_state
        mock_store.get_state_by_version_number.assert_called_once_with("KA-BLR-001", 2)

    @pytest.mark.asyncio
    async def test_get_state_version_not_found(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.return_value = None
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 5 not found for location 'KA-BLR-001'"):
            await mgr.get_state_version("KA-BLR-001", 5)

    @pytest.mark.asyncio
    async def test_update_state(self, mock_store, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_latest_state.return_value = base_twin_state
        version = TwinStateVersion(
            entity_id="KA-BLR-001",
            version_number=2,
            state=TwinState(
                entity_id="KA-BLR-001",
                timestamp=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
                temperature_2m=30.0,
                precipitation_mm=15.0,
                humidity_pct=70.0,
                pressure_hpa=1012.0,
                wind_speed_10m=6.0,
                wind_direction_10m=200.0,
            ),
        )
        mock_store.save_state.return_value = version
        mgr = TwinStateManager(store=mock_store)

        delta = StateDelta(
            entity_id="KA-BLR-001",
            from_version_id="v1",
            to_version_id="v2",
            delta_temperature=1.5,
            delta_precipitation=5.0,
            delta_humidity=5.0,
            delta_pressure=-1.0,
            delta_wind_speed=1.0,
            delta_wind_direction=20.0,
        )
        result = await mgr.update_state("KA-BLR-001", delta, source="manual")
        assert result == version
        mock_store.save_state.assert_called_once()
        args, _ = mock_store.save_state.call_args
        saved_state = args[0]
        assert saved_state.temperature_2m == 30.0
        assert saved_state.precipitation_mm == 15.0

    @pytest.mark.asyncio
    async def test_update_state_no_current(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_latest_state.return_value = None
        version = MagicMock()
        version.version_id = "v1"
        version.version_number = 1
        mock_store.save_state.return_value = version
        mgr = TwinStateManager(store=mock_store)

        delta = StateDelta(
            entity_id="KA-BLR-001",
            from_version_id="",
            to_version_id="",
            delta_temperature=25.0,
            delta_humidity=60,
        )
        result = await mgr.update_state("KA-BLR-001", delta)
        assert result is version
        # store.save_state should have been called with initial state
        mock_store.save_state.assert_called_once()
        saved_state = mock_store.save_state.call_args[0][0]
        assert saved_state.temperature_2m == 25.0
        assert saved_state.humidity_pct == 60
        assert saved_state.quality_flag == "initial"

    @pytest.mark.asyncio
    async def test_rollback_success(self, mock_store, base_twin_state):
        import pyarrow as pa

        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.return_value = base_twin_state
        index = pa.table(
            {
                "entity_id": ["KA-BLR-001", "KA-BLR-001"],
                "version_id": ["vid-1", "vid-2"],
                "version_number": [1, 2],
                "created_at": [datetime.now(UTC), datetime.now(UTC)],
                "created_by": ["system", "system"],
                "parent_version_id": ["", "vid-1"],
                "description": ["initial", "update"],
                "file_path": ["f1.parquet", "f2.parquet"],
            }
        )
        mock_store._read_version_index.return_value = index
        mock_store.rollback.return_value = base_twin_state
        mgr = TwinStateManager(store=mock_store)

        result = await mgr.rollback("KA-BLR-001", 1)
        assert result == base_twin_state
        mock_store.rollback.assert_called_once_with("KA-BLR-001", "vid-1")

    @pytest.mark.asyncio
    async def test_rollback_version_not_found(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.return_value = None
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 99 not found for location 'KA-BLR-001'"):
            await mgr.rollback("KA-BLR-001", 99)

    @pytest.mark.asyncio
    async def test_rollback_version_not_in_index(self, mock_store, base_twin_state):
        import pyarrow as pa

        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.return_value = base_twin_state
        index = pa.table(
            {
                "entity_id": [],
                "version_id": [],
                "version_number": [],
                "created_at": [],
                "created_by": [],
                "parent_version_id": [],
                "description": [],
                "file_path": [],
            }
        )
        mock_store._read_version_index.return_value = index
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 1 not found for location 'KA-BLR-001'"):
            await mgr.rollback("KA-BLR-001", 1)

    @pytest.mark.asyncio
    async def test_get_version_history(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        versions = [
            TwinStateVersion(entity_id="KA-BLR-001", version_number=2),
            TwinStateVersion(entity_id="KA-BLR-001", version_number=1),
        ]
        mock_store.get_version_history.return_value = versions
        mgr = TwinStateManager(store=mock_store)

        result = await mgr.get_version_history("KA-BLR-001")
        assert len(result) == 2
        mock_store.get_version_history.assert_called_once_with("KA-BLR-001")

    @pytest.mark.asyncio
    async def test_compare_versions(self, mock_store, base_twin_state):
        import pyarrow as pa

        from simulator.state_manager.twin_state_manager import TwinStateManager

        state_b = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
            temperature_2m=30.0,
            precipitation_mm=15.0,
            humidity_pct=70.0,
            pressure_hpa=1012.0,
            wind_speed_10m=6.0,
            wind_direction_10m=200.0,
        )
        mock_store.get_state_by_version_number.side_effect = [base_twin_state, state_b]
        index = pa.table(
            {
                "entity_id": ["KA-BLR-001", "KA-BLR-001"],
                "version_id": ["vid-1", "vid-2"],
                "version_number": [1, 2],
                "created_at": [datetime.now(UTC), datetime.now(UTC)],
                "created_by": ["system", "system"],
                "parent_version_id": ["", "vid-1"],
                "description": ["initial", "update"],
                "file_path": ["f1.parquet", "f2.parquet"],
            }
        )
        mock_store._read_version_index.return_value = index
        delta = StateDelta(entity_id="KA-BLR-001", from_version_id="vid-1", to_version_id="vid-2")
        mock_store.compute_delta.return_value = delta
        mgr = TwinStateManager(store=mock_store)

        result = await mgr.compare_versions("KA-BLR-001", 1, 2)
        assert result is delta
        mock_store.compute_delta.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_versions_first_not_found(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.side_effect = [None, MagicMock()]
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 1 not found"):
            await mgr.compare_versions("KA-BLR-001", 1, 2)

    @pytest.mark.asyncio
    async def test_compare_versions_second_not_found(self, mock_store, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_state_by_version_number.side_effect = [base_twin_state, None]
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 2 not found for location 'KA-BLR-001'"):
            await mgr.compare_versions("KA-BLR-001", 1, 2)

    @pytest.mark.asyncio
    async def test_compare_versions_find_version_id_fails(self, mock_store, base_twin_state):
        import pyarrow as pa

        from simulator.state_manager.twin_state_manager import TwinStateManager

        state_b = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
            temperature_2m=30.0,
            precipitation_mm=15.0,
            humidity_pct=70.0,
            pressure_hpa=1012.0,
            wind_speed_10m=6.0,
            wind_direction_10m=200.0,
        )
        mock_store.get_state_by_version_number.side_effect = [base_twin_state, state_b]
        index = pa.table(
            {
                "entity_id": ["KA-BLR-001"],
                "version_id": ["vid-1"],
                "version_number": [1],
                "created_at": [datetime.now(UTC)],
                "created_by": ["system"],
                "parent_version_id": [""],
                "description": ["initial"],
                "file_path": ["f1.parquet"],
            }
        )
        mock_store._read_version_index.return_value = index
        mgr = TwinStateManager(store=mock_store)

        with pytest.raises(ValueError, match="Version 2 not found"):
            await mgr.compare_versions("KA-BLR-001", 1, 2)

    @pytest.mark.asyncio
    async def test_sync_observation(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        obs = WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=28.5,
            precipitation_mm=10.0,
            humidity_pct=65.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
            data_source=DataSource.IMD,
            quality_flag=QualityFlag.VALIDATED,
        )
        version = TwinStateVersion(entity_id="KA-BLR-001", version_number=1)
        mock_store.save_state.return_value = version
        mgr = TwinStateManager(store=mock_store)

        result = await mgr.sync_observation(obs)
        assert result is version
        mock_store.save_state.assert_called_once()
        args, _ = mock_store.save_state.call_args
        saved = args[0]
        assert saved.entity_id == "KA-BLR-001"
        assert saved.temperature_2m == 28.5
        assert saved.data_source == "imd"
        assert saved.quality_flag == "validated"

    @pytest.mark.asyncio
    async def test_query_spatial(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.query_spatial.return_value = []
        mgr = TwinStateManager(store=mock_store)

        result = await mgr.query_spatial((10.0, 75.0, 15.0, 80.0))
        assert result == []
        mock_store.query_spatial.assert_called_once_with((10.0, 75.0, 15.0, 80.0))

    @pytest.mark.asyncio
    async def test_detect_conflicts(self, mock_conflict_resolver):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_conflict_resolver.detect_conflicts.return_value = []
        mgr = TwinStateManager(conflict_resolver=mock_conflict_resolver)

        result = await mgr.detect_conflicts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_conflicts(self, mock_conflict_resolver):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_conflict_resolver.resolve_all.return_value = []
        mgr = TwinStateManager(conflict_resolver=mock_conflict_resolver)

        result = await mgr.resolve_conflicts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_reconcile(self, mock_store, mock_reconciler, base_twin_state):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store.get_latest_state.return_value = base_twin_state
        rec_result = ReconciliationResult(
            entity_id="KA-BLR-001",
            original_state=base_twin_state,
            reconciled_state=base_twin_state,
        )
        mock_reconciler.reconcile = AsyncMock(return_value=rec_result)
        mgr = TwinStateManager(store=mock_store, reconciler=mock_reconciler)

        result = await mgr.reconcile("KA-BLR-001", primary_source="imd")
        assert result == rec_result
        mock_reconciler.reconcile.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_entity_to_graph(self, mock_store, mock_graph):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mgr = TwinStateManager(store=mock_store, graph=mock_graph)
        await mgr.add_entity_to_graph("KA-BLR-001", 12.97, 77.59, name="Bengaluru")
        mock_graph.add_entity.assert_called_once()
        mock_store.register_entity_location.assert_called_once_with("KA-BLR-001", 12.97, 77.59)

    @pytest.mark.asyncio
    async def test_get_graph_neighbors(self, mock_graph):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_graph.get_neighbors.return_value = []
        mgr = TwinStateManager(graph=mock_graph)
        result = await mgr.get_graph_neighbors("KA-BLR-001", RelationshipType.AFFECTS)
        assert result == []
        mock_graph.get_neighbors.assert_called_once_with("KA-BLR-001", RelationshipType.AFFECTS)

    @pytest.mark.asyncio
    async def test_query_within_distance(self, mock_graph):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_graph.query_within_distance.return_value = []
        mgr = TwinStateManager(graph=mock_graph)
        result = await mgr.query_within_distance(12.97, 77.59, 50.0)
        assert result == []

    @pytest.mark.asyncio
    async def test_health(self, mock_store):
        from simulator.state_manager.twin_state_manager import TwinStateManager

        mock_store._version_index_path.exists.return_value = True
        mgr = TwinStateManager(store=mock_store)
        health = await mgr.health()
        assert health["status"] == "healthy"
        assert health["store_initialized"] is True
        assert "graph_entity_count" in health
        assert health["version_index_exists"] is True


class TestAddOptional:
    def test_both_none(self):
        from simulator.state_manager.twin_state_manager import _add_optional

        assert _add_optional(None, None) is None

    def test_base_none(self):
        from simulator.state_manager.twin_state_manager import _add_optional

        assert _add_optional(None, 5.0) == 5.0

    def test_delta_none(self):
        from simulator.state_manager.twin_state_manager import _add_optional

        assert _add_optional(10.0, None) == 10.0

    def test_both_values(self):
        from simulator.state_manager.twin_state_manager import _add_optional

        assert _add_optional(10.0, 5.0) == 15.0
