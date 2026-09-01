from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "15"))


class DisasterClient:
    def twin_overlay(self, location: str) -> dict[str, Any]:
        resp = requests.get(
            f"{API_BASE_URL}/disaster/twin/{location}",
            timeout=CLIENT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def relief(self, assessment_id: str) -> dict[str, Any]:
        resp = requests.post(
            f"{API_BASE_URL}/disaster/relief/plan",
            json={"assessment_id": assessment_id},
            timeout=CLIENT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def assessment(self, assessment_id: str) -> dict[str, Any]:
        resp = requests.get(
            f"{API_BASE_URL}/disaster/assessments/{assessment_id}",
            timeout=CLIENT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
