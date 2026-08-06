from __future__ import annotations

from datetime import UTC, datetime

from pipeline.providers.fetch_result import (
    AUTH_REQUIRED,
    INVALID_RESPONSE,
    NO_DATA,
    RATE_LIMITED,
    REQUEST_FAILED,
    SOURCE_UNAVAILABLE,
    FetchResult,
)
from simulator.models.weather import DataSource


class TestFetchResult:
    def test_success_result(self):
        result = FetchResult(
            provider=DataSource.OPEN_METEO,
            status="SUCCESS",
            observations=["obs1", "obs2"],
        )
        assert result.status == "SUCCESS"
        assert len(result.observations) == 2
        assert result.error_code is None

    def test_failure_result(self):
        result = FetchResult(
            provider=DataSource.OPEN_METEO,
            status="FAILED",
            observations=[],
            error_code=RATE_LIMITED,
            error_message="Too many requests",
        )
        assert result.status == "FAILED"
        assert result.observations == []
        assert result.error_code == "RATE_LIMITED"

    def test_no_observation_for_failure(self):
        result = FetchResult(
            provider=DataSource.OPEN_METEO,
            status="FAILED",
            observations=[],
        )
        assert len(result.observations) == 0

    def test_error_codes(self):
        assert SOURCE_UNAVAILABLE == "SOURCE_UNAVAILABLE"
        assert REQUEST_FAILED == "REQUEST_FAILED"
        assert AUTH_REQUIRED == "AUTH_REQUIRED"
        assert RATE_LIMITED == "RATE_LIMITED"
        assert INVALID_RESPONSE == "INVALID_RESPONSE"
        assert NO_DATA == "NO_DATA"

    def test_request_metadata(self):
        result = FetchResult(
            provider=DataSource.OPEN_METEO,
            status="SUCCESS",
            observations=[],
            requested_at=datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 7, 30, 12, 0, 5, tzinfo=UTC),
            request_metadata={"latitude": 12.97, "longitude": 77.59},
        )
        assert result.requested_at is not None
        assert result.completed_at is not None
        assert result.request_metadata["latitude"] == 12.97
