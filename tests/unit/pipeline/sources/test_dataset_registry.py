import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pipeline.sources.dataset_registry import DatasetRegistry


class TestDatasetRegistry:
    def test_default_path(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            reg = DatasetRegistry()
        expected = tmp_path / ".climatedt" / "datasets" / "dataset_registry.json"
        assert str(reg._registry_file) == str(expected.resolve())

    def test_custom_path(self, tmp_path):
        custom = tmp_path / "custom" / "reg.json"
        reg = DatasetRegistry(registry_path=custom)
        assert str(reg._registry_file) == str(custom.resolve())

    def test_initial_entries_empty(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        assert reg._entries == []

    def test_load_from_existing_file(self, tmp_path):
        reg_path = tmp_path / "reg.json"
        entries = [{"dataset_id": "abc123", "status": "completed"}]
        reg_path.write_text(json.dumps(entries))
        reg = DatasetRegistry(registry_path=reg_path)
        assert reg._entries == entries

    def test_load_corrupted_json(self, tmp_path):
        reg_path = tmp_path / "reg.json"
        reg_path.write_text("not valid json")
        reg = DatasetRegistry(registry_path=reg_path)
        assert reg._entries == []

    def test_load_os_error(self, tmp_path):
        reg_path = tmp_path / "reg.json"
        reg_path.mkdir()
        reg = DatasetRegistry(registry_path=reg_path)
        assert reg._entries == []

    def test_save_creates_parent_dir(self, tmp_path):
        reg_path = tmp_path / "sub" / "deep" / "reg.json"
        reg = DatasetRegistry(registry_path=reg_path)
        reg.register_dataset("t", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg_path.exists()

    def test_register_dataset_with_checksum(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        did = reg.register_dataset(
            "test", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"], checksum="abc123"
        )
        assert len(did) == 16
        assert reg._entries[0]["checksum"] == "abc123"

    def test_register_dataset_auto_checksum(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        did = reg.register_dataset("test", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert len(did) == 16
        assert len(reg._entries[0]["checksum"]) == 64

    def test_register_dataset_with_metadata(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset(
            "test", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"], metadata={"key": "val"}
        )
        assert json.loads(reg._entries[0]["metadata_json"]) == {"key": "val"}

    def test_register_with_record_count_and_parquet_path(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset(
            "test",
            (date(2020, 1, 1), date(2020, 1, 10)),
            ["loc1"],
            record_count=100,
            parquet_path="/data/test.parquet",
        )
        assert reg._entries[0]["record_count"] == 100
        assert reg._entries[0]["parquet_path"] == "/data/test.parquet"

    def test_get_ingestion_status_found(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg.get_ingestion_status("src", date(2020, 1, 5)) == "completed"

    def test_get_ingestion_status_wrong_source(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg.get_ingestion_status("other", date(2020, 1, 5)) is None

    def test_get_ingestion_status_outside_range(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg.get_ingestion_status("src", date(2020, 2, 1)) is None

    def test_list_datasets(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        result = reg.list_datasets()
        assert len(result) == 1
        assert result[0]["source_name"] == "src"

    def test_list_datasets_returns_copy(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        result = reg.list_datasets()
        result.append({"extra": True})
        assert len(reg._entries) == 1

    def test_get_dataset_by_checksum_found(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        did = reg.register_dataset(
            "src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"], checksum="abc123"
        )
        entry = reg.get_dataset_by_checksum("abc123")
        assert entry is not None
        assert entry["dataset_id"] == did

    def test_get_dataset_by_checksum_not_found(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg.get_dataset_by_checksum("nonexistent") is None

    def test_clear_with_file(self, tmp_path):
        reg_path = tmp_path / "reg.json"
        reg = DatasetRegistry(registry_path=reg_path)
        reg.register_dataset("src", (date(2020, 1, 1), date(2020, 1, 10)), ["loc1"])
        assert reg_path.exists()
        reg.clear()
        assert reg._entries == []
        assert not reg_path.exists()

    def test_clear_without_file(self, tmp_path):
        reg = DatasetRegistry(registry_path=tmp_path / "reg.json")
        reg._entries.append({"test": True})
        reg.clear()
        assert reg._entries == []
