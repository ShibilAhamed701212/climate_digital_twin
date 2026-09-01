from __future__ import annotations

import logging

import httpx

from disaster_intelligence.domain.entities import TwinOverlayPointer

logger = logging.getLogger(__name__)


class NullTwinPointerAdapter:
    def upsert(self, pointer: TwinOverlayPointer) -> None:
        _ = pointer


class HttpTwinPointerAdapter:
    def __init__(self, twin_url: str, timeout_s: float = 5.0) -> None:
        self._url = twin_url.rstrip("/")
        self._timeout = timeout_s

    def upsert(self, pointer: TwinOverlayPointer) -> None:
        last_exc: Exception | None = None
        for _ in range(3):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(f"{self._url}/overlay-pointer", json=pointer.to_dict())
                    if resp.status_code < 400:
                        return
                    last_exc = RuntimeError(f"HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                last_exc = exc
        logger.warning("Twin overlay pointer sync failed: %s", last_exc)
        raise RuntimeError(str(last_exc))
