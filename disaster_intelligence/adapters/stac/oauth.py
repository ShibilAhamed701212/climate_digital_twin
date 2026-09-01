from __future__ import annotations

import os
import threading
import time
from typing import Any

import httpx

from disaster_intelligence.domain.errors import DisasterError

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
SENTINEL_HUB_TOKEN_URL = (
    "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
)

_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def _cached(key: str, expires_in: float, token: str) -> str:
    with _TOKEN_LOCK:
        _TOKEN_CACHE[key] = (token, time.time() + max(30.0, expires_in - 60.0))
    return token


def _from_cache(key: str) -> str | None:
    with _TOKEN_LOCK:
        hit = _TOKEN_CACHE.get(key)
        if hit and hit[1] > time.time():
            return hit[0]
    return None


def reset_token_cache() -> None:
    with _TOKEN_LOCK:
        _TOKEN_CACHE.clear()


def cdse_access_token(timeout_s: float = 20.0) -> str | None:
    """Password grant against the public CDSE client. Returns None if unset."""
    user = os.environ.get("CDSE_USERNAME", "").strip()
    password = os.environ.get("CDSE_PASSWORD", "").strip()
    if not user or not password:
        return None
    cached = _from_cache("cdse")
    if cached:
        return cached
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                CDSE_TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": user,
                    "password": password,
                    "client_id": "cdse-public",
                },
            )
            if resp.status_code >= 400:
                raise DisasterError(f"CDSE token HTTP {resp.status_code}", "STAC_ERROR")
            payload = resp.json() or {}
            token = payload.get("access_token")
            if not token:
                return None
            expires = float(payload.get("expires_in") or 600)
            return _cached("cdse", expires, str(token))
    except httpx.HTTPError as exc:
        raise DisasterError(f"CDSE token unreachable: {exc}", "STAC_ERROR") from exc


def sentinel_hub_access_token(timeout_s: float = 20.0) -> str | None:
    client_id = os.environ.get("SH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    cached = _from_cache("sentinel_hub")
    if cached:
        return cached
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                SENTINEL_HUB_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            if resp.status_code >= 400:
                raise DisasterError(
                    f"Sentinel Hub token HTTP {resp.status_code}",
                    "STAC_ERROR",
                )
            payload = resp.json() or {}
            token = payload.get("access_token")
            if not token:
                return None
            expires = float(payload.get("expires_in") or 600)
            return _cached("sentinel_hub", expires, str(token))
    except httpx.HTTPError as exc:
        raise DisasterError(f"Sentinel Hub token unreachable: {exc}", "STAC_ERROR") from exc


def earthdata_auth() -> tuple[str, str] | None:
    user = os.environ.get("EARTHDATA_USERNAME", "").strip()
    password = os.environ.get("EARTHDATA_PASSWORD", "").strip()
    if user and password:
        return user, password
    return None


def earthdata_token() -> str | None:
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    return token or None


def credential_status() -> dict[str, Any]:
    return {
        "cdse": bool(os.environ.get("CDSE_USERNAME") and os.environ.get("CDSE_PASSWORD")),
        "sentinel_hub": bool(os.environ.get("SH_CLIENT_ID") and os.environ.get("SH_CLIENT_SECRET")),
        "earthdata": bool(
            os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD")
        )
        or bool(os.environ.get("EARTHDATA_TOKEN")),
        "planetary_computer": True,
        "planet": bool(os.environ.get("PLANET_API_KEY")),
        "maxar": bool(os.environ.get("MAXAR_API_KEY")),
        "gee": bool(os.environ.get("EARTHENGINE_TOKEN")),
        "radiant": bool(os.environ.get("RADIANT_API_KEY")),
        "worldpop_fetch": os.environ.get("WORLD_POP_FETCH", "").strip().lower()
        in {"1", "true", "yes", "on"},
        "nasadem_fetch": os.environ.get("NASADEM_FETCH", "").strip().lower()
        in {"1", "true", "yes", "on"},
    }
