"""Unit tests for simulator/repository/."""

from pathlib import Path

import pytest

from simulator.repository.parquet_repository import ParquetRepository
from simulator.state_manager.version import Version


class TestParquetRepository:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> ParquetRepository:
        return ParquetRepository(store_dir=str(tmp_path / "twin_store"))

    def test_save_and_load_versions(self, repo: ParquetRepository):
        v1 = Version(version_id=1, location_id="KA-BLR-001", entity_data={"rainfall": 10})
        v2 = Version(version_id=2, location_id="KA-BLR-001", entity_data={"rainfall": 20})
        repo.save_version(v1)
        repo.save_version(v2)
        versions = repo.load_versions("KA-BLR-001")
        assert len(versions) == 2
        assert versions[0].version_id == 1
        assert versions[1].version_id == 2

    def test_load_latest_version(self, repo: ParquetRepository):
        repo.save_version(Version(1, "KA-BLR-001", {"rainfall": 10}))
        repo.save_version(Version(2, "KA-BLR-001", {"rainfall": 20}))
        latest = repo.load_latest_version("KA-BLR-001")
        assert latest is not None
        assert latest.version_id == 2

    def test_load_latest_nonexistent(self, repo: ParquetRepository):
        assert repo.load_latest_version("NONEXISTENT") is None

    def test_load_versions_empty(self, repo: ParquetRepository):
        assert repo.load_versions("NONEXISTENT") == []

    def test_load_all_location_ids(self, repo: ParquetRepository):
        repo.save_version(Version(1, "LOC-001", {}))
        repo.save_version(Version(1, "LOC-002", {}))
        ids = repo.load_all_location_ids()
        assert "LOC-001" in ids
        assert "LOC-002" in ids

    def test_delete_location(self, repo: ParquetRepository):
        repo.save_version(Version(1, "KA-BLR-001", {"rainfall": 10}))
        repo.delete_location("KA-BLR-001")
        assert repo.load_versions("KA-BLR-001") == []

    def test_version_roundtrip_preserves_data(self, repo: ParquetRepository):
        data = {
            "location_id": "KA-BLR-001",
            "latitude": 12.97,
            "longitude": 77.59,
            "rainfall": 45.5,
            "max_temp": 32.0,
        }
        v = Version(version_id=1, location_id="KA-BLR-001", entity_data=data)
        repo.save_version(v)
        loaded = repo.load_versions("KA-BLR-001")
        assert loaded[0].entity_data["rainfall"] == 45.5
        assert loaded[0].entity_data["max_temp"] == 32.0

    def test_cache_consistency(self, repo: ParquetRepository):
        repo.save_version(Version(1, "LOC-001", {"a": 1}))
        repo.save_version(Version(2, "LOC-001", {"a": 2}))
        v1 = repo.load_versions("LOC-001")
        v2 = repo.load_versions("LOC-001")
        assert len(v1) == len(v2)
