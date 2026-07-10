from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.warning("Invalid %s '%s', using default %s", key, val, default)
        return default


@dataclass
class GatewayConfig:
    host: str = field(default_factory=lambda: os.environ.get("GATEWAY_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("GATEWAY_PORT", 8000))
    debug: bool = field(
        default_factory=lambda: os.environ.get("GATEWAY_DEBUG", "false").lower() == "true"
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "GATEWAY_CORS_ORIGINS", "http://localhost:3000,http://localhost:8501"
        ).split(",")
    )
    api_key_enabled: bool = field(default=True)
    api_key: str = field(default_factory=lambda: os.environ.get("GATEWAY_API_KEY", ""))
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    app_title: str = "Climate Digital Twin API"
    app_version: str = "0.1.0"
    app_description: str = (
        "Unified REST API for the Climate Digital Twin platform. "
        "Provides endpoints for risk assessment, scenario simulation, "
        "forecasting, RAG knowledge retrieval, feedback capture, "
        "and digital twin state management."
    )


_config: GatewayConfig | None = None


def get_gateway_config() -> GatewayConfig:
    global _config
    if _config is None:
        _config = GatewayConfig()
    if _config.api_key_enabled and not _config.api_key:
        logger.warning(
            "GATEWAY_API_KEY_ENABLED is true but GATEWAY_API_KEY is not set. "
            "Disabling API key auth."
        )
        _config.api_key_enabled = False
    return _config


def configure_gateway(**kwargs: object) -> GatewayConfig:
    global _config
    existing = get_gateway_config()
    for key, value in kwargs.items():
        if not hasattr(existing, key):
            raise TypeError(f"Unknown configuration option: {key}")
        setattr(existing, key, value)
    return existing
