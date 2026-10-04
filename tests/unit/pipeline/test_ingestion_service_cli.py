"""Tests for pipeline.ingestion_service and the pipeline.ingest CLI."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from pipeline import ingest as ingest_cli
from pipeline import ingestion_service as svc_module
from pipeline.ingestion_service import IngestionService, _resolve_provider
from pipeline.providers.fetch_result import FetchResult
from simulator.models.weather import DataSource, WeatherObservation


def _obs() -> WeatherObservation:
    return WeatherObservation(
        location_id="blr",
        latitude=12.97,
        longitude=77.59,
        timestamp=datetime.now(UTC) - timedelta(hours=1),
        temperature_2m=27.5,
        precipitation_mm=3.2,
        humidity_pct=70.0,
        pressure_hpa=912.0,
        wind_speed_10m=3.1,
        wind_direction_10m=180.0,
        data_source=DataSource.OPEN_METEO,
    )


def _ok(**_kwargs) -> FetchResult:
    return FetchResult(
        provider=DataSource.OPEN_METEO,
        status="SUCCESS",
        observations=[_obs()],
        request_metadata={"endpoint": "https://example.invalid/forecast"},
    )


def _fail(**_kwargs) -> FetchResult:
    return FetchResult(
        provider=DataSource.NASA_POWER,
        status="FAILED",
        observations=[],
        error_code="SOURCE_UNAVAILABLE",
        error_message="down",
    )


@pytest.mark.parametrize(
    ("intent", "override", "expected"),
    [
        ("recent", None, ["open_meteo", "nasa_power"]),
        ("forecast", None, ["open_meteo"]),
        ("historical", None, ["nasa_power", "open_meteo"]),
        ("recent", "imd", ["imd"]),
    ],
)
def test_resolve_provider(intent, override, expected) -> None:
    assert _resolve_provider(intent, override) == expected


@pytest.fixture
def service(tmp_path, monkeypatch) -> IngestionService:
    monkeypatch.chdir(tmp_path)
    return IngestionService({"data_dir": str(tmp_path / "real")})


def test_falls_back_to_next_provider_and_persists(service, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(svc_module, "fetch_nasa_power", _fail)
    monkeypatch.setattr(svc_module, "fetch_open_meteo", _ok)

    result = service.run_single(12.97, 77.59, intent="historical")

    assert result["status"] == "SUCCESS"
    assert result["provider"] == "open_meteo"
    assert result["records_received"] == 1
    assert result["records_validated"] == 1
    assert result["records_rejected"] == 0
    assert result["values"]["temperature_2m"] == 27.5
    assert list((tmp_path / "real").rglob("*.parquet"))


def test_all_providers_failing_reports_last_error(service, monkeypatch) -> None:
    monkeypatch.setattr(svc_module, "fetch_open_meteo", _fail)
    monkeypatch.setattr(svc_module, "fetch_nasa_power", _fail)

    result = service.run_single(12.97, 77.59)

    assert result["status"] == "FAILED"
    assert result["records_persisted"] == 0
    assert result["error"].startswith("nasa_power: SOURCE_UNAVAILABLE")


def test_validate_observations_splits_rejected(service) -> None:
    class _O:
        def __init__(self, flag: str) -> None:
            self.quality_flag = flag

    valid, rejected = service._validate_observations([_O("raw"), _O("rejected"), _O("ok")])

    assert len(valid) == 2 and len(rejected) == 1


class TestCli:
    @pytest.fixture
    def fake_service(self, monkeypatch):
        calls: list[dict] = []
        result: dict = {}

        class _Svc:
            def run_single(self, **kwargs):
                calls.append(kwargs)
                return result

        monkeypatch.setattr(ingest_cli, "IngestionService", _Svc)
        return calls, result

    def test_json_output_success(self, fake_service, capsys) -> None:
        calls, result = fake_service
        result.update({"status": "SUCCESS", "run_id": "r1"})

        code = ingest_cli.main(["--provider", "open_meteo", "--output", "json"])

        assert code == 0
        assert calls[0]["provider_override"] == "open_meteo"
        assert json.loads(capsys.readouterr().out)["run_id"] == "r1"

    def test_text_output_success(self, fake_service, capsys) -> None:
        calls, result = fake_service
        result.update(
            {
                "status": "SUCCESS",
                "run_id": "r2",
                "provider": "open_meteo",
                "latitude": 12.97,
                "longitude": 77.59,
                "observation_timestamp": "2026-01-01T00:00:00Z",
                "ingestion_timestamp": "2026-01-01T00:05:00Z",
                "values": {"temperature_2m": 27.5},
                "units": {"temperature_2m": "C"},
                "paths": {"raw": "data/real/raw/x.json", "rejected": None},
            }
        )

        code = ingest_cli.main(["--intent", "auto", "--verbose"])

        out = capsys.readouterr().out
        assert code == 0
        assert calls[0] == {
            "lat": 12.9716,
            "lon": 77.5946,
            "intent": "recent",
            "provider_override": None,
        }
        assert "temperature_2m" in out and "data/real/raw/x.json" in out

    def test_text_output_failure_returns_1(self, fake_service, capsys) -> None:
        _, result = fake_service
        result.update({"status": "FAILED", "run_id": "r3", "error": "all down"})

        assert ingest_cli.main([]) == 1
        assert "all down" in capsys.readouterr().out
