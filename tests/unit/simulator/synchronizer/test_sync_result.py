from simulator.synchronizer.sync_result import (
    CREATED,
    FAILED,
    LOCATION_MISMATCH,
    NO_STATE_CHANGE,
    OUT_OF_ORDER,
    REJECTED_QUALITY,
    REJECTED_SYNTHETIC,
    SKIPPED_DUPLICATE,
    UPDATED,
    SyncResult,
)


def test_sync_result_defaults():
    r = SyncResult(status=CREATED, location_id="KA-BLR")
    assert r.status == CREATED
    assert r.location_id == "KA-BLR"
    assert r.observation_id == ""
    assert r.old_version == 0
    assert r.new_version == 0
    assert r.changed_variables == []
    assert r.error is None


def test_sync_result_full():
    r = SyncResult(
        status=UPDATED,
        location_id="KA-BLR",
        observation_id="obs_123",
        run_id="run_001",
        provider="open_meteo",
        authenticity="REAL",
        old_version=1,
        new_version=2,
        changed_variables=["temperature_2m", "humidity_pct"],
    )
    assert r.status == UPDATED
    assert r.old_version == 1
    assert r.new_version == 2


def test_sync_result_error():
    r = SyncResult(
        status=REJECTED_SYNTHETIC,
        location_id="KA-BLR",
        error="Authenticity is SYNTHETIC",
    )
    assert r.status == REJECTED_SYNTHETIC
    assert r.error == "Authenticity is SYNTHETIC"


def test_all_statuses_defined():
    assert CREATED == "CREATED"
    assert UPDATED == "UPDATED"
    assert NO_STATE_CHANGE == "NO_STATE_CHANGE"
    assert SKIPPED_DUPLICATE == "SKIPPED_DUPLICATE"
    assert OUT_OF_ORDER == "OUT_OF_ORDER"
    assert REJECTED_QUALITY == "REJECTED_QUALITY"
    assert REJECTED_SYNTHETIC == "REJECTED_SYNTHETIC"
    assert LOCATION_MISMATCH == "LOCATION_MISMATCH"
    assert FAILED == "FAILED"
