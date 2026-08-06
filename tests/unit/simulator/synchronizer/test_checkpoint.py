import tempfile
from pathlib import Path

from simulator.synchronizer.checkpoint import SyncCheckpoint


def test_checkpoint_is_processed():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        assert not cp.is_processed("KA-BLR", "obs_001")
        cp.mark_processed("KA-BLR", "obs_001", "CREATED")
        assert cp.is_processed("KA-BLR", "obs_001")


def test_checkpoint_get_result():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        cp.mark_processed("KA-BLR", "obs_001", "UPDATED")
        assert cp.get_result("KA-BLR", "obs_001") == "UPDATED"


def test_checkpoint_persistence():
    path = Path(tempfile.mktemp(suffix=".json"))
    try:
        cp1 = SyncCheckpoint(path)
        cp1.mark_processed("KA-BLR", "obs_001", "CREATED")
        cp2 = SyncCheckpoint(path)
        assert cp2.is_processed("KA-BLR", "obs_001")
        assert cp2.get_result("KA-BLR", "obs_001") == "CREATED"
    finally:
        if path.exists():
            path.unlink()


def test_checkpoint_batch():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        cp.mark_batch(
            [
                ("KA-BLR", "obs_001", "CREATED"),
                ("KA-BLR", "obs_002", "UPDATED"),
                ("KA-MYS", "obs_003", "SKIPPED_DUPLICATE"),
            ]
        )
        assert cp.is_processed("KA-BLR", "obs_001")
        assert cp.is_processed("KA-MYS", "obs_003")
        assert not cp.is_processed("KA-BLR", "obs_999")


def test_checkpoint_get_processed_ids():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        cp.mark_processed("KA-BLR", "obs_001", "CREATED")
        cp.mark_processed("KA-BLR", "obs_002", "UPDATED")
        ids = cp.get_processed_ids("KA-BLR")
        assert "obs_001" in ids
        assert "obs_002" in ids
        assert "obs_003" not in ids


def test_checkpoint_get_all_location_ids():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        cp.mark_processed("KA-BLR", "obs_001", "CREATED")
        cp.mark_processed("KA-MYS", "obs_002", "CREATED")
        locs = cp.get_all_location_ids()
        assert "KA-BLR" in locs
        assert "KA-MYS" in locs


def test_checkpoint_clear():
    with tempfile.TemporaryDirectory() as tmp:
        cp = SyncCheckpoint(Path(tmp) / "checkpoint.json")
        cp.mark_processed("KA-BLR", "obs_001", "CREATED")
        cp.clear()
        assert not cp.is_processed("KA-BLR", "obs_001")
