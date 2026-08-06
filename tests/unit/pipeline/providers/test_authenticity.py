from __future__ import annotations

from pipeline.providers.authenticity import DataAuthenticity


class TestDataAuthenticity:
    def test_values(self):
        assert DataAuthenticity.REAL.value == "REAL"
        assert DataAuthenticity.SYNTHETIC.value == "SYNTHETIC"

    def test_independent_from_status(self):
        from pipeline.providers.manager import ObservationStatus

        for auth in DataAuthenticity:
            for status in ObservationStatus:
                assert auth.value != status.value
