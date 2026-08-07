"""Unit tests for simulator/synchronizer/twin_health.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from simulator.synchronizer.twin_health import get_all_twin_health, get_twin_health


def test_get_twin_health():
    mock_service = MagicMock()
    mock_service.get_twin_freshness.return_value = {"location_id": "KA-BLR-001", "status": "fresh"}
    res = get_twin_health("KA-BLR-001", sync_service=mock_service)
    assert res["status"] == "fresh"
    mock_service.get_twin_freshness.assert_called_once_with("KA-BLR-001")


def test_get_all_twin_health():
    mock_service = MagicMock()
    mock_service.checkpoint.get_all_location_ids.return_value = ["KA-BLR-001", "KA-MYS-001"]
    mock_service.get_twin_freshness.side_effect = lambda loc: {"location_id": loc, "status": "ok"}
    res = get_all_twin_health(sync_service=mock_service)
    assert len(res) == 2
    assert res[0]["location_id"] == "KA-BLR-001"
