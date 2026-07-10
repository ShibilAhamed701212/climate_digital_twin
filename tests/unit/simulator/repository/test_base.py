from simulator.repository.base import TwinRepository


class TestTwinRepositoryABC:
    def test_save_version_body(self):
        assert TwinRepository.save_version(None, None) is None

    def test_load_versions_body(self):
        assert TwinRepository.load_versions(None, None) is None

    def test_load_latest_version_body(self):
        assert TwinRepository.load_latest_version(None, None) is None

    def test_load_all_location_ids_body(self):
        assert TwinRepository.load_all_location_ids(None) is None

    def test_delete_location_body(self):
        assert TwinRepository.delete_location(None, None) is None
