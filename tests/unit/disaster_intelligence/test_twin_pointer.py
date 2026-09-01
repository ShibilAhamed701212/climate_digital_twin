"""Regression: DIE HttpTwinPointerAdapter must POST /overlay-pointer on Twin."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from disaster_intelligence.adapters.http.twin_pointer import HttpTwinPointerAdapter
from disaster_intelligence.domain.entities import TwinOverlayPointer
from simulator.api.main import app


def test_twin_app_registers_overlay_pointer_routes() -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/overlay-pointer" in paths
    assert "/overlay-pointer/{location_id}" in paths


def test_http_twin_pointer_adapter_404_without_route(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reproduce the live HTTP 404 when Twin has no overlay-pointer route."""

    class _Resp:
        status_code = 404

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args, kwargs

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def post(self, url: str, json: dict) -> _Resp:
            assert url.endswith("/overlay-pointer")
            _ = json
            return _Resp()

    monkeypatch.setattr(
        "disaster_intelligence.adapters.http.twin_pointer.httpx.Client",
        _Client,
    )
    adapter = HttpTwinPointerAdapter("http://127.0.0.1:8001")
    pointer = TwinOverlayPointer(
        location_id="KA-HAS-001",
        assessment_id="A1",
        event_id="E1",
        disaster_type="flood",
        href_assessment="/disaster/assessments/A1",
        updated_at="2026-01-01T00:00:00Z",
    )
    with pytest.raises(RuntimeError, match="HTTP 404"):
        adapter.upsert(pointer)


def test_http_twin_pointer_adapter_posts_existing_twin_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args, kwargs

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *args: object) -> None:
            _ = args

        def post(self, url: str, json: dict):
            assert url.rstrip("/").endswith("/overlay-pointer")
            return client.post("/overlay-pointer", json=json)

    monkeypatch.setattr(
        "disaster_intelligence.adapters.http.twin_pointer.httpx.Client",
        _Client,
    )
    adapter = HttpTwinPointerAdapter("http://twin-state-mgr:8001")
    pointer = TwinOverlayPointer(
        location_id="KA-HAS-001",
        assessment_id="01M03HG8M5H2146TMPZAMKJGPN",
        event_id="E1",
        disaster_type="flood",
        href_assessment="/disaster/assessments/01M03HG8M5H2146TMPZAMKJGPN",
        updated_at="2026-01-01T00:00:00Z",
        kpis={"flood_area_km2": 0.02},
    )
    adapter.upsert(pointer)
    got = client.get("/overlay-pointer/KA-HAS-001")
    assert got.status_code == 200
    body = got.json()
    assert body["assessment_id"] == "01M03HG8M5H2146TMPZAMKJGPN"
    assert body["href_assessment"].startswith("/disaster/assessments/")
