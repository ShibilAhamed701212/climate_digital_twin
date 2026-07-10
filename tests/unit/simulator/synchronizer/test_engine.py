"""Unit tests for simulator/synchronizer/engine.py."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simulator.models.twin_state import TwinState
from simulator.models.weather import WeatherObservation


@pytest.fixture
def mock_state_manager():
    mgr = MagicMock()
    mgr.store = MagicMock()
    return mgr


@pytest.fixture
def mock_observation_store():
    return MagicMock()


@pytest.fixture
def mock_baseline_computer():
    comp = MagicMock()
    comp.compute_full_climatology.return_value = MagicMock(
        daily=[1, 2, 3],
        monthly=[1, 2],
        seasonal=[1],
        version="v1",
    )
    return comp


@pytest.fixture
def mock_anomaly_detector():
    detector = MagicMock()
    detector.detect_anomalies.return_value = MagicMock(anomalies=[])
    return detector


@pytest.fixture
def base_observation():
    return WeatherObservation(
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
    )


def _create_sync(base_dir: Path, **overrides):
    """Helper to create a TwinSynchronizer with a real temp directory."""
    from simulator.synchronizer.engine import TwinSynchronizer

    sync = TwinSynchronizer(**overrides)
    sync_dir = base_dir / "sync_history"
    sync_dir.mkdir(parents=True, exist_ok=True)
    sync._sync_history_path = str(sync_dir / "sync_history.parquet")
    return sync


class TestTwinSynchronizer:
    def test_init_defaults(self):
        from simulator.synchronizer.engine import TwinSynchronizer

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.sync_history = "sync_history"
            mock_cfg.return_value = cfg
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer()
                assert sync._state_manager is not None
                assert sync._observation_store is not None

    def test_init_with_dependencies(
        self,
        mock_state_manager,
        mock_observation_store,
        mock_baseline_computer,
        mock_anomaly_detector,
    ):
        from simulator.synchronizer.engine import TwinSynchronizer

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.sync_history = "sync_history"
            mock_cfg.return_value = cfg
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    observation_store=mock_observation_store,
                    baseline_computer=mock_baseline_computer,
                    anomaly_detector=mock_anomaly_detector,
                )
                assert sync._state_manager is mock_state_manager
                assert sync._observation_store is mock_observation_store

    @pytest.mark.asyncio
    async def test_sync_observations_no_data(self, mock_state_manager):
        from simulator.synchronizer.engine import TwinSynchronizer

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(state_manager=mock_state_manager)

        result = await sync.sync_observations_to_twin("KA-BLR-001", [])
        assert result["status"] == "no_data"
        assert result["observations_synced"] == 0

    @pytest.mark.asyncio
    async def test_sync_first_observation(self, mock_state_manager, base_observation):
        from simulator.synchronizer.engine import TwinSynchronizer

        mock_state_manager.get_current_state = AsyncMock(side_effect=ValueError("No state"))
        mock_state_manager.store.save_state.return_value = MagicMock()

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                with patch.object(TwinSynchronizer, "_record_sync") as mock_record:
                    sync = TwinSynchronizer(state_manager=mock_state_manager)
                    result = await sync.sync_observations_to_twin("KA-BLR-001", [base_observation])
                    assert result["status"] == "success"
                    assert result["observations_synced"] == 1
                    mock_state_manager.store.save_state.assert_called_once()
                    mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_multiple_observations(self, mock_state_manager, mock_anomaly_detector):
        from simulator.synchronizer.engine import TwinSynchronizer

        existing_state = TwinState(
            entity_id="KA-BLR-001",
            timestamp=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
            temperature_2m=28.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1015.0,
            wind_speed_10m=4.0,
            wind_direction_10m=180.0,
        )
        mock_state_manager.get_current_state = AsyncMock(return_value=existing_state)
        mock_state_manager.update_state = AsyncMock(return_value=MagicMock())

        obs1 = WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 11, 0, tzinfo=UTC),
            temperature_2m=29.0,
            precipitation_mm=10.0,
            humidity_pct=65.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
        )
        obs2 = WeatherObservation(
            location_id="KA-BLR-001",
            latitude=12.97,
            longitude=77.59,
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            temperature_2m=30.0,
            precipitation_mm=15.0,
            humidity_pct=70.0,
            pressure_hpa=1011.0,
            wind_speed_10m=6.0,
            wind_direction_10m=200.0,
        )

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    anomaly_detector=mock_anomaly_detector,
                )

        with patch.object(TwinSynchronizer, "_record_sync"):
            result = await sync.sync_observations_to_twin("KA-BLR-001", [obs1, obs2])
        assert result["status"] == "success"
        assert result["observations_synced"] == 2

    @pytest.mark.asyncio
    async def test_sync_historical_baseline(self, mock_state_manager, mock_baseline_computer):
        from simulator.synchronizer.engine import TwinSynchronizer

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    baseline_computer=mock_baseline_computer,
                )

        result = await sync.sync_historical_baseline("KA-BLR-001", 1991, 2020, "era5")
        assert result["status"] == "success"
        assert result["total_records"] == 6
        assert result["daily_records"] == 3
        assert result["monthly_records"] == 2
        assert result["seasonal_records"] == 1
        mock_baseline_computer.compute_full_climatology.assert_called_once_with(
            location_id="KA-BLR-001",
            start_year=1991,
            end_year=2020,
            source="era5",
        )
        mock_baseline_computer.save_climatology.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_historical_state_no_data(self, mock_state_manager, mock_observation_store):
        from simulator.synchronizer.engine import TwinSynchronizer

        mock_observation_store.query_observations.return_value = []

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    observation_store=mock_observation_store,
                )

        result = await sync.build_historical_state("KA-BLR-001", 1991, 2020)
        assert result["status"] == "no_data"
        assert result["synced"] == 0

    @pytest.mark.asyncio
    async def test_build_historical_state_with_data(
        self, mock_state_manager, mock_observation_store, base_observation
    ):
        from simulator.synchronizer.engine import TwinSynchronizer

        mock_observation_store.query_observations.return_value = [base_observation]
        mock_state_manager.get_current_state = AsyncMock(side_effect=ValueError("No state"))
        mock_state_manager.store.save_state.return_value = MagicMock()

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    observation_store=mock_observation_store,
                )

        with patch.object(TwinSynchronizer, "_record_sync"):
            result = await sync.build_historical_state("KA-BLR-001", 1991, 2020)
        assert result["status"] == "success"
        assert result["observations_synced"] == 1

    @pytest.mark.asyncio
    async def test_sync_full_location(
        self, mock_state_manager, mock_baseline_computer, mock_observation_store, base_observation
    ):
        from simulator.synchronizer.engine import TwinSynchronizer

        mock_observation_store.query_observations.return_value = [base_observation]
        mock_state_manager.get_current_state = AsyncMock(side_effect=ValueError("No state"))
        mock_state_manager.store.save_state.return_value = MagicMock()

        with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(sync_history="sync_history")
            with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                mock_res.return_value = MagicMock()
                sync = TwinSynchronizer(
                    state_manager=mock_state_manager,
                    observation_store=mock_observation_store,
                    baseline_computer=mock_baseline_computer,
                )

        with patch.object(TwinSynchronizer, "_record_sync"):
            result = await sync.sync_full_location("KA-BLR-001")
        assert result["status"] == "success"
        assert result["baseline"]["status"] == "success"
        assert result["historical_state"]["status"] == "success"

    def test_record_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from simulator.synchronizer.engine import TwinSynchronizer

            with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
                mock_cfg.return_value = MagicMock(sync_history="sync_history")
                with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                    mock_res.return_value = Path(tmpdir)
                    sync = TwinSynchronizer()
                    sync._record_sync(
                        location_id="KA-BLR-001",
                        sync_type="incremental",
                        start_time=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
                        end_time=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
                        synced_count=5,
                        anomaly_count=0,
                        status="success",
                    )

            import pyarrow.parquet as pq

            table = pq.read_table(sync._sync_history_path)
            assert table.num_rows == 1
            assert str(table.column("location_id")[0].as_py()) == "KA-BLR-001"

    def test_record_sync_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from simulator.synchronizer.engine import TwinSynchronizer

            with patch("simulator.synchronizer.engine.get_config") as mock_cfg:
                mock_cfg.return_value = MagicMock(sync_history="sync_history")
                with patch("simulator.synchronizer.engine.resolve_subdir") as mock_res:
                    mock_res.return_value = Path(tmpdir)
                    sync = TwinSynchronizer()
                    sync._record_sync(
                        location_id="KA-BLR-001",
                        sync_type="incremental",
                        start_time=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
                        end_time=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
                        synced_count=5,
                        anomaly_count=0,
                        status="success",
                    )
                    sync._record_sync(
                        location_id="KA-BLR-002",
                        sync_type="full",
                        start_time=datetime(2024, 6, 2, 12, 0, tzinfo=UTC),
                        end_time=datetime(2024, 6, 2, 13, 0, tzinfo=UTC),
                        synced_count=3,
                        anomaly_count=1,
                        status="success",
                    )

            import pyarrow.parquet as pq

            table = pq.read_table(sync._sync_history_path)
            assert table.num_rows == 2
            assert str(table.column("location_id")[0].as_py()) == "KA-BLR-001"
            assert str(table.column("location_id")[1].as_py()) == "KA-BLR-002"
