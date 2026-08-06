from __future__ import annotations

from typing import Any

from simulator.synchronizer.twin_sync_service import TwinSyncService


def get_twin_health(
    location_id: str,
    sync_service: TwinSyncService | None = None,
) -> dict[str, Any]:
    service = sync_service or TwinSyncService()
    return service.get_twin_freshness(location_id)


def get_all_twin_health(sync_service: TwinSyncService | None = None) -> list[dict[str, Any]]:
    service = sync_service or TwinSyncService()
    location_ids = service.checkpoint.get_all_location_ids()
    results = []
    for loc_id in location_ids:
        results.append(service.get_twin_freshness(loc_id))
    return results
