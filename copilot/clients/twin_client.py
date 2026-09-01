from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

TWIN_SERVICE_URL = os.environ.get("TWIN_SERVICE_URL", "http://localhost:8001")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


class TwinClient:
    def get_current_state(
        self,
        location: str,
        timeout: float = CLIENT_TIMEOUT,
    ) -> dict[str, Any]:
        resp = requests.get(
            f"{TWIN_SERVICE_URL}/state/current",
            params={"location_id": location},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
