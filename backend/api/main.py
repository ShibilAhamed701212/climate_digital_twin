from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from backend.api.config import get_gateway_config
from backend.api.middleware import setup_middleware
from backend.api.routes import (
    copilot_proxy,
    disaster,
    feedback,
    forecast,
    health,
    rag,
    risk,
    scenario,
    twin,
    twin_proxy,
)

_logger = logging.getLogger(__name__)


def _unique_operation_id(route: APIRoute) -> str:
    methods = "_".join(sorted(m.lower() for m in route.methods if m not in {"HEAD", "OPTIONS"}))
    return f"{route.name}_{methods}" or route.name


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    config = get_gateway_config()

    _logger.info(
        "Climate Digital Twin API v%s starting up",
        config.app_version,
    )
    from backend.api.dependencies import (
        get_feedback_capture,
        get_risk_service,
        get_scenario_service,
        get_twin_manager,
    )

    services_ok = 0
    for name, fn in [
        ("risk", get_risk_service),
        ("scenario", get_scenario_service),
        ("feedback", get_feedback_capture),
        ("twin", get_twin_manager),
    ]:
        try:
            fn()
            services_ok += 1
            _logger.info("%s service initialized", name)
        except ModuleNotFoundError as e:
            _logger.warning("%s service unavailable (will proxy): %s", name, e)
    _logger.info("%d/4 services initialized", services_ok)

    yield

    _logger.info(
        "Climate Digital Twin API v%s shutting down",
        config.app_version,
    )


def create_app() -> FastAPI:
    config = get_gateway_config()

    app = FastAPI(
        title=config.app_title,
        description=config.app_description,
        version=config.app_version,
        docs_url=config.docs_url,
        openapi_url=config.openapi_url,
        lifespan=lifespan,
        generate_unique_id_function=_unique_operation_id,
    )

    app.include_router(health.router)
    app.include_router(risk.router)
    app.include_router(scenario.router)
    app.include_router(rag.router)
    app.include_router(feedback.router)
    app.include_router(twin.router)
    app.include_router(twin_proxy.router)
    app.include_router(forecast.router)
    app.include_router(disaster.router)
    app.include_router(copilot_proxy.router)

    setup_middleware(app)

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "error_code": "BAD_REQUEST",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        _logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred",
                "error_code": "INTERNAL_ERROR",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": config.app_title,
            "version": config.app_version,
            "docs": config.docs_url,
            "openapi": config.openapi_url,
        }

    return app


app = create_app()


def main() -> None:
    import uvicorn

    config = get_gateway_config()
    uvicorn.run(
        "backend.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
