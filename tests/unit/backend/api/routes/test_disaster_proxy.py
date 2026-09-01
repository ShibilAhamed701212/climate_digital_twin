from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.config import GatewayConfig
from backend.api.main import create_app


def test_disaster_proxy_maps_502(monkeypatch) -> None:
    # Reset singleton so patched get_gateway_config is invoked
    import backend.api.config as cfg_module
    cfg_module._config = None

    cfg = GatewayConfig(api_key_enabled=False, disaster_engine_url="http://127.0.0.1:65500")
    with patch("backend.api.routes.disaster.get_gateway_config", return_value=cfg):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/disaster/models")
        assert resp.status_code == 502
        assert resp.json()["error_code"] == "DISASTER_UNAVAILABLE"


def test_disaster_proxy_forwards_ok() -> None:
    cfg = GatewayConfig(api_key_enabled=False, disaster_engine_url="http://die.test")

    class _Resp:
        status_code = 200
        content = b'{"items":[]}'
        headers = {"content-type": "application/json"}

    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=_Resp())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    import backend.api.config as cfg_module
    cfg_module._config = None

    with (
        patch("backend.api.routes.disaster.get_gateway_config", return_value=cfg),
        patch("backend.api.routes.disaster.httpx.AsyncClient", return_value=mock_client),
    ):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/disaster/models")
        assert resp.status_code == 200
        assert resp.json() == {"items": []}


def test_disaster_proxy_streams_sse() -> None:
    cfg = GatewayConfig(api_key_enabled=False, disaster_engine_url="http://die.test")

    class _Resp:
        status_code = 200
        headers = {"content-type": "text/event-stream"}

        async def aiter_bytes(self):
            yield b'data: {"stage":"done"}\n\n'

        async def aclose(self):
            return None

    mock_client = MagicMock()
    mock_client.build_request = MagicMock(return_value=object())
    mock_client.send = AsyncMock(return_value=_Resp())
    mock_client.aclose = AsyncMock()

    import backend.api.config as cfg_module
    cfg_module._config = None

    with (
        patch("backend.api.routes.disaster.get_gateway_config", return_value=cfg),
        patch("backend.api.routes.disaster.httpx.AsyncClient", return_value=mock_client),
    ):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/disaster/jobs/job1/stream")
        assert resp.status_code == 200
        assert b"stage" in resp.content
        mock_client.send.assert_awaited()


def test_disaster_proxy_streams_geojson() -> None:
    cfg = GatewayConfig(api_key_enabled=False, disaster_engine_url="http://die.test")

    class _Resp:
        status_code = 200
        headers = {"content-type": "application/geo+json"}

        async def aiter_bytes(self):
            yield b'{"type":"FeatureCollection","features":[]}'

        async def aclose(self):
            return None

    mock_client = MagicMock()
    mock_client.build_request = MagicMock(return_value=object())
    mock_client.send = AsyncMock(return_value=_Resp())
    mock_client.aclose = AsyncMock()

    import backend.api.config as cfg_module
    cfg_module._config = None

    with (
        patch("backend.api.routes.disaster.get_gateway_config", return_value=cfg),
        patch("backend.api.routes.disaster.httpx.AsyncClient", return_value=mock_client),
    ):
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/disaster/assessments/a1/geojson")
        assert resp.status_code == 200
        assert b"FeatureCollection" in resp.content
        mock_client.send.assert_awaited()
