from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.disaster_client import API_BASE_URL, DisasterClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DisasterIntelligenceTool(BaseTool):
    def __init__(self) -> None:
        self._name = "disaster_intelligence"
        self._description = (
            "Query disaster intelligence overlays: flood extent, OSM impact, relief ranks"
        )
        self._client = DisasterClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        location = kwargs.get("location", "KA-BLR-001")
        action = kwargs.get("action", "summary")
        started = time.monotonic()
        try:
            overlay = self._client.twin_overlay(location)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if not overlay.get("available"):
                return {
                    "tool": self._name,
                    "location": location,
                    "available": False,
                    "error": "No verified disaster assessment is available.",
                    "processing_ms": elapsed_ms,
                }
            payload: dict[str, Any] = {
                "tool": self._name,
                "location": location,
                "available": True,
                "overlay": overlay,
                "quality_flags": overlay.get("quality_flags") or [],
                "model_cards": overlay.get("model_cards") or {},
                "model_id": overlay.get("model_id")
                or (overlay.get("model_cards") or {}).get("flood"),
                "model_version": overlay.get("model_version") or "0",
                "runtime": overlay.get("runtime")
                or (overlay.get("model_cards") or {}).get("runtime"),
                "confidence_type": overlay.get("confidence_type")
                or (overlay.get("model_cards") or {}).get("confidence_type"),
                "sensor": overlay.get("sensor") or (overlay.get("model_cards") or {}).get("sensor"),
                "polarization": overlay.get("polarization")
                or (overlay.get("model_cards") or {}).get("polarization"),
                "fallback_used": overlay.get("fallback_used")
                or (overlay.get("model_cards") or {}).get("fallback_used"),
                "authenticity": overlay.get("authenticity"),
                "confidence_mean": overlay.get("confidence_mean"),
                "provenance": overlay.get("model_cards") or {},
                "source": f"/disaster/twin/{location}",
                "processing_ms": elapsed_ms,
            }
            assessment_id = overlay.get("assessment_id")
            if action == "relief" and assessment_id:
                payload["relief"] = self._client.relief(str(assessment_id))
            if action in {"infra", "geojson_stats"}:
                payload["kpis"] = overlay.get("kpis") or {}
            return payload
        except (ConnectionError, Timeout, HTTPError, KeyError, TypeError) as exc:
            logger.warning("Disaster service unavailable: %s", exc)
            return {
                "tool": self._name,
                "location": location,
                "available": False,
                "error": "No verified disaster assessment is available.",
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        action = kwargs.get("action", "summary")
        if action not in {"summary", "infra", "relief", "geojson_stats"}:
            return False, "action must be summary, infra, relief, or geojson_stats"
        if "location" in kwargs and not isinstance(kwargs["location"], str):
            return False, "location must be a string"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {"location": "str", "action": "str"},
        }

    def health_check(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{API_BASE_URL}/disaster/models", timeout=2)
            if resp.ok:
                return True, "disaster_intelligence healthy"
            return False, f"disaster HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)
