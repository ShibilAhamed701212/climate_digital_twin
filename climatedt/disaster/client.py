from __future__ import annotations

import os
from typing import Any

import httpx


class DisasterHttpClient:
    """Python facade used by risk/scenario/report callers."""

    def __init__(self, base_url: str | None = None, timeout_s: float = 8.0) -> None:
        self._base = (
            base_url or os.environ.get("DISASTER_ENGINE_URL") or "http://localhost:8008"
        ).rstrip("/")
        self._timeout = timeout_s

    def twin_overlay(self, location_id: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self._base}/disaster/twin/{location_id}")
                if resp.status_code >= 400:
                    return {"available": False, "location_id": location_id}
                return resp.json()
        except httpx.HTTPError:
            return {"available": False, "location_id": location_id}

    def assessment(self, assessment_id: str) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self._base}/disaster/assessments/{assessment_id}")
                if resp.status_code >= 400:
                    return None
                return resp.json()
        except httpx.HTTPError:
            return None
