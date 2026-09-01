"""Proxy routes for the Copilot Agent service (port 8005)."""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Request, Response

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["Copilot"])

_COPILOT_URL = os.environ.get("COPILOT_API_URL", "http://127.0.0.1:8005")


async def _proxy(request: Request) -> Response:
    base = _COPILOT_URL.rstrip("/")
    path = request.url.path
    # Strip the /copilot prefix — the service uses root-level routes
    if path.startswith("/copilot/"):
        path = path[len("/copilot") :]
    elif path == "/copilot":
        path = "/"
    url = f"{base}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}
    }
    body = await request.body()
    timeout = httpx.Timeout(120.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                request.method,
                url,
                content=body if body else None,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        _logger.warning("Copilot service unavailable: %s", exc)
        return Response(
            content='{"detail":"Copilot service unavailable","error_code":"COPILOT_UNAVAILABLE"}',
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
    operation_id="copilot_proxy_get",
)
async def copilot_proxy_get(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["POST"],
    operation_id="copilot_proxy_post",
)
async def copilot_proxy_post(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["PUT"],
    operation_id="copilot_proxy_put",
)
async def copilot_proxy_put(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["PATCH"],
    operation_id="copilot_proxy_patch",
)
async def copilot_proxy_patch(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)


@router.api_route(
    "/{full_path:path}",
    methods=["DELETE"],
    operation_id="copilot_proxy_delete",
)
async def copilot_proxy_delete(full_path: str, request: Request) -> Response:
    _ = full_path
    return await _proxy(request)
