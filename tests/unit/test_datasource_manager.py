"""Tests for DataSourceManager — central climate data authority."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock


from pipeline.providers.manager import (
    DataSourceManager,
    Observation,
    ObservationStatus,
)


class TestObservationStatus:
    def test_status_values(self):
        assert ObservationStatus.LIVE.value == "LIVE"
        assert ObservationStatus.CACHED.value == "CACHED"
        assert ObservationStatus.HISTORICAL.value == "HISTORICAL"
        assert ObservationStatus.UNAVAILABLE.value == "UNAVAILABLE"

    def test_status_order(self):
        assert ObservationStatus.LIVE != ObservationStatus.CACHED
        assert ObservationStatus.CACHED != ObservationStatus.HISTORICAL
        assert ObservationStatus.HISTORICAL != ObservationStatus.UNAVAILABLE


class TestObservation:
    def test_unavailable_defaults(self):
        obs = Observation.unavailable("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.UNAVAILABLE
        assert obs.location_id == "KA-BLR-001"
        assert obs.variable == "temperature_2m"
        assert "No verified climate observations" in obs.message

    def test_unavailable_custom_message(self):
        obs = Observation.unavailable("KA-BLR-001", "rainfall", "Custom error")
        assert obs.message == "Custom error"


class TestDataSourceManager:
    def test_unavailable_when_no_providers(self):
        dsm = DataSourceManager()
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.UNAVAILABLE
        assert "No verified climate observations available" in obs.message

    def test_unavailable_when_all_providers_fail(self):
        dsm = DataSourceManager()
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.side_effect = ConnectionError("API down")
        dsm._providers = [mock_provider]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.UNAVAILABLE

    def test_live_from_first_provider(self):
        dsm = DataSourceManager()
        live_obs = Observation(
            status=ObservationStatus.LIVE,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 31.2},
        )
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.return_value = live_obs
        dsm._providers = [mock_provider]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.LIVE
        assert obs.provider == "NASA POWER"
        assert obs.values["temperature_2m"] == 31.2

    def test_historical_fallback_when_providers_fail(self):
        dsm = DataSourceManager()
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.side_effect = ConnectionError("API down")
        dsm._providers = [mock_provider]
        historical_obs = Observation(
            status=ObservationStatus.HISTORICAL,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 28.5},
            dataset_version="1981-2011_archive_v1",
        )
        mock_historical = MagicMock()
        mock_historical.lookup.return_value = historical_obs
        dsm._historical_store = mock_historical
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.HISTORICAL
        assert obs.dataset_version == "1981-2011_archive_v1"

    def test_provider_priority_order(self):
        dsm = DataSourceManager()
        first = MagicMock()
        first.is_available.return_value = True
        first.fetch.side_effect = ConnectionError("fail")
        second = MagicMock()
        second.is_available.return_value = True
        second.fetch.return_value = Observation(
            status=ObservationStatus.LIVE,
            provider="Open-Meteo",
            location_id="KA-BLR-001",
            variable="temperature_2m",
        )
        dsm._providers = [first, second]
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.LIVE
        assert obs.provider == "Open-Meteo"

    def test_cache_fallback_before_historical(self):
        dsm = DataSourceManager()
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.side_effect = ConnectionError("fail")
        dsm._providers = [mock_provider]
        cached_obs = Observation(
            status=ObservationStatus.CACHED,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 30.0},
        )
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_obs
        dsm._cache = mock_cache
        mock_historical = MagicMock()
        dsm._historical_store = mock_historical
        obs = dsm.get_observation("KA-BLR-001", "temperature_2m")
        assert obs.status == ObservationStatus.CACHED
        mock_historical.lookup.assert_not_called()

    def test_live_saves_to_cache(self):
        dsm = DataSourceManager()
        live_obs = Observation(
            status=ObservationStatus.LIVE,
            provider="NASA POWER",
            location_id="KA-BLR-001",
            variable="temperature_2m",
            values={"temperature_2m": 31.2},
        )
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.fetch.return_value = live_obs
        dsm._providers = [mock_provider]
        mock_cache = MagicMock()
        dsm._cache = mock_cache
        dsm.get_observation("KA-BLR-001", "temperature_2m")
        mock_cache.save.assert_called_once_with(live_obs)

    def test_retrieved_timestamp_set_on_unavailable(self):
        obs = DataSourceManager().get_observation("KA-BLR-001", "rainfall")
        assert obs.retrieved_timestamp != ""
        datetime.fromisoformat(obs.retrieved_timestamp)


class TestHistoricalStore:
    def test_lookup_returns_none_when_no_data(self, tmp_path):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore(data_dir=str(tmp_path))
        obs = store.lookup("KA-BLR-001", "temperature_2m")
        assert obs is None

    def test_lookup_returns_none_for_unknown_variable(self):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore()
        obs = store.lookup("KA-BLR-001", "nonexistent_var")
        assert obs is None

    def test_lookup_real_data_rainfall(self):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore()
        obs = store.lookup("KA-BLR-001", "rainfall")
        assert obs is not None
        assert obs.status == ObservationStatus.HISTORICAL
        assert obs.provider == "NASA POWER"
        assert "rainfall" in obs.values
        assert obs.dataset_version is not None

    def test_lookup_real_data_temperature(self):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore()
        obs = store.lookup("KA-BLR-001", "temperature_2m")
        assert obs is not None
        assert obs.status == ObservationStatus.HISTORICAL
        assert obs.provider == "NASA POWER"
        assert "temperature_2m" in obs.values
        assert isinstance(obs.values["temperature_2m"], float)

    def test_lookup_real_data_min_temp(self):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore()
        obs = store.lookup("KA-BLR-001", "temperature_2m_min")
        assert obs is not None
        assert obs.status == ObservationStatus.HISTORICAL
        assert "temperature_2m_min" in obs.values

    def test_is_available_true_when_data_exists(self):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore()
        assert store.is_available() is True

    def test_is_available_false_when_no_data(self, tmp_path):
        from pipeline.providers.historical_store import HistoricalStore
        store = HistoricalStore(data_dir=str(tmp_path))
        assert store.is_available() is False
