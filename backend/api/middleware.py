from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.config import get_gateway_config
from backend.api.rate_limit import take_token

_logger = logging.getLogger(__name__)

_AUTH_EXEMPT_PATHS = {"/health", "/health/ready", "/health/live", "/", "/docs", "/openapi.json"}

_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 300


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        response.headers["X-Request-Timing-Ms"] = f"{elapsed_ms:.1f}"

        if elapsed_ms > 1000:
            _logger.warning(
                "Slow request: %s %s took %.1fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )

        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            _logger.exception(
                "Unhandled error processing %s %s: %s",
                request.method,
                request.url.path,
                exc,
            )
            raise


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path.rstrip("/")
        if path in _AUTH_EXEMPT_PATHS or path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        bucket = "default"
        limit = _RATE_LIMIT_MAX
        if path.startswith("/disaster/ingest/upload"):
            bucket = "die_upload"
            limit = 5
        elif path.startswith("/disaster/jobs") or path.startswith("/disaster/ingest"):
            bucket = "die_jobs"
            limit = 20
        elif "/stream" in path or "/layers/" in path:
            bucket = "die_stream"
            limit = 600
        elif path.startswith("/disaster"):
            bucket = "die_read"
            limit = 120

        allowed, retry_after, remaining = take_token(
            f"{client_ip}:{bucket}", limit, _RATE_LIMIT_WINDOW
        )
        if not allowed:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "error_code": "TOO_MANY_REQUESTS",
                    "retry_after_seconds": max(1, retry_after),
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        config = get_gateway_config()

        if not config.api_key_enabled:
            return await call_next(request)

        path = request.url.path.rstrip("/")
        if path in _AUTH_EXEMPT_PATHS or any(
            path.startswith(exempt) for exempt in {"/health", "/docs", "/openapi"}
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing API key. Provide it via Authorization: Bearer <key>",
                    "error_code": "UNAUTHORIZED",
                },
            )

        api_key = auth_header.removeprefix("Bearer ")

        if not secrets.compare_digest(api_key, config.api_key):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid API key",
                    "error_code": "UNAUTHORIZED",
                },
            )

        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    config = get_gateway_config()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(RateLimiterMiddleware)

    app.add_middleware(APIKeyAuthMiddleware)

    app.add_middleware(ErrorLoggingMiddleware)

    app.add_middleware(RequestTimingMiddleware)

    _logger.info(
        "Middleware configured: CORS origins=%s, auth=%s, timing=enabled, error_logging=enabled",
        config.cors_origins,
        "enabled" if config.api_key_enabled else "disabled",
    )
