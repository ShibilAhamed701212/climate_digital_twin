"""Unit tests for simulator/sync.py CLI main function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from simulator.sync import main


def test_sync_main_health():
    with patch("simulator.sync.get_twin_health") as mock_health:
        mock_health.return_value = {"location_id": "KA-BLR-001", "status": "fresh"}
        ret = main(["--health", "KA-BLR-001", "--output", "json"])
        assert ret == 0
        mock_health.assert_called_once_with("KA-BLR-001")


def test_sync_main_health_all():
    with patch("simulator.sync.get_all_twin_health") as mock_health_all:
        mock_health_all.return_value = [{"location_id": "KA-BLR-001", "status": "fresh"}]
        ret = main(["--health-all"])
        assert ret == 0
        mock_health_all.assert_called_once()


def test_sync_main_sync_only():
    with (
        patch("simulator.sync.TwinSyncService") as mock_service_cls,
        patch("simulator.sync.ObservationStore"),
    ):
        mock_service = mock_service_cls.return_value
        mock_service.sync_pending_observations.return_value = []
        ret = main(["--sync-only", "--verbose", "--output", "json"])
        assert ret == 0


def test_sync_main_full():
    with (
        patch("simulator.sync.TwinSyncService") as mock_service_cls,
        patch("simulator.sync.ObservationStore") as mock_obs_cls,
    ):
        mock_service = mock_service_cls.return_value
        mock_obs = mock_obs_cls.return_value
        obs1 = MagicMock(provider="open_meteo")
        mock_obs.query.return_value = [obs1]

        res_mock = MagicMock(
            status="SYNCED",
            location_id="KA-BLR",
            observation_id="obs-1",
            run_id="run-1",
            provider="open_meteo",
            authenticity="verified",
            old_version=1,
            new_version=2,
            changed_variables=["temp"],
            error=None,
        )
        mock_service.sync_from_observation.return_value = res_mock

        ret = main(["--provider", "open_meteo", "--location", "KA-BLR"])
        assert ret == 0
