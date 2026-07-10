from unittest.mock import MagicMock

from simulator.engine.twin_engine import DigitalTwinEngine


class TestDigitalTwinEngine:
    def test_get_historical_state(self):
        mock_service = MagicMock()
        mock_service.get_historical_state.return_value = [{"location_id": "loc1"}]
        engine = DigitalTwinEngine.__new__(DigitalTwinEngine)
        engine.service = mock_service
        result = engine.get_historical_state("loc1")
        assert result == [{"location_id": "loc1"}]
        mock_service.get_historical_state.assert_called_once_with("loc1", None)
