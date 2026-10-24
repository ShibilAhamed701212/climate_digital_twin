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
    api_key_enabled: bool = field(
        default_factory=lambda: os.environ.get("GATEWAY_API_KEY_ENABLED", "false").lower() == "true"
    )
    api_key: str = field(default_factory=lambda: os.environ.get("GATEWAY_API_KEY", ""))
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    app_title: str = "Climate Digital Twin API"
    app_version: str = "2.1.0"
    app_description: str = (
        "Unified REST API for the Climate Digital Twin platform. "
        "Provides endpoints for risk assessment, scenario simulation, "
        "forecasting, RAG knowledge retrieval, feedback capture, "
        "digital twin state management, and disaster intelligence."
    )
    disaster_engine_url: str = field(
        default_factory=lambda: os.environ.get("DISASTER_ENGINE_URL", "http://127.0.0.1:8008")
    )
    disaster_proxy_timeout_s: float = field(
        default_factory=lambda: float(os.environ.get("DISASTER_PROXY_TIMEOUT_S", "120"))
    )
    twin_engine_url: str = field(
        default_factory=lambda: os.environ.get("TWIN_ENGINE_URL", "http://127.0.0.1:8001")
    )
    twin_proxy_timeout_s: float = field(
        default_factory=lambda: float(os.environ.get("TWIN_PROXY_TIMEOUT_S", "120"))
    )


_config: GatewayConfig | None = None
_warned_missing_key = False


def get_gateway_config() -> GatewayConfig:
    global _config, _warned_missing_key
    if _config is None:
        _config = GatewayConfig()
    if _config.api_key_enabled and not _config.api_key and not _warned_missing_key:
        # Fail closed: auth stays enabled and protected routes answer 503 until
        # a key is configured (previously auth was silently switched off).
        logger.error(
            "GATEWAY_API_KEY_ENABLED is true but GATEWAY_API_KEY is not set. "
            "Protected endpoints will reject requests until a key is configured."
        )
        _warned_missing_key = True
    return _config


def configure_gateway(**kwargs: object) -> GatewayConfig:
    global _config
    existing = get_gateway_config()
    for key, value in kwargs.items():
        if not hasattr(existing, key):
            raise TypeError(f"Unknown configuration option: {key}")
        setattr(existing, key, value)
    return existing
