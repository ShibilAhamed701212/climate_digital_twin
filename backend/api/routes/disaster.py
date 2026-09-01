from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from backend.api.config import get_gateway_config

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disaster", tags=["Disaster Intelligence"])


def _should_stream(path: str) -> bool:
    lowered = path.lower()
    return (
        lowered.endswith("/stream")
        or lowered.endswith("/geojson")
        or lowered.endswith("/mask")
        or "/layers/" in lowered
    )


async def _proxy(request: Request) -> Response:
    config = get_gateway_config()
    base = config.disaster_engine_url.rstrip("/")
    path = request.url.path
    url = f"{base}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    body = await request.body()
    timeout = httpx.Timeout(config.disaster_proxy_timeout_s, connect=5.0)
    is_stream = _should_stream(path)
    if path.endswith("/stream"):
        timeout = httpx.Timeout(900.0, connect=5.0)
    try:
        if is_stream:
            client = httpx.AsyncClient(timeout=timeout)
            try:
                req = client.build_request(
                    request.method,
                    url,
                    content=body if body else None,
                    headers=headers,
                )
                resp = await client.send(req, stream=True)
            except Exception:
                await client.aclose()
                raise
            excluded = {"content-encoding", "transfer-encoding", "connection"}
            out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
            out_headers["Cache-Control"] = "no-cache"
            out_headers["X-Accel-Buffering"] = "no"

            async def gen():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()

            return StreamingResponse(
                gen(),
                status_code=resp.status_code,
                headers=out_headers,
                media_type=resp.headers.get("content-type", "text/event-stream"),
            )
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                request.method,
                url,
                content=body if body else None,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        _logger.warning("Disaster engine unavailable: %s", exc)
        return Response(
            content='{"detail":"Disaster Intelligence Engine unavailable","error_code":"DISASTER_UNAVAILABLE"}',
            status_code=502,
            media_type="application/json",
        )
    excluded = {"content-encoding", "transfer-encoding", "connection"}
    out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=out_headers,
        media_type=resp.headers.get("content-type"),
    )


@router.api_route(
    "/{full_path:path}",
    methods=["GET"],
    operation_id="disaster_proxy_get",
)
async def disaster_proxy_get(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["POST"],
    operation_id="disaster_proxy_post",
)
async def disaster_proxy_post(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["PUT"],
    operation_id="disaster_proxy_put",
)
async def disaster_proxy_put(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["PATCH"],
    operation_id="disaster_proxy_patch",
)
async def disaster_proxy_patch(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["DELETE"],
    operation_id="disaster_proxy_delete",
)
async def disaster_proxy_delete(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)
