from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

SCENARIO_SERVICE_URL = os.environ.get("SCENARIO_SERVICE_URL", "http://scenario-engine:8002")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


class ScenarioClient:
    def simulate(
        self,
        location: str,
        scenario_type: str,
        value: float,
        timeout: float = CLIENT_TIMEOUT,
    ) -> dict[str, Any]:
        resp = requests.post(
            f"{SCENARIO_SERVICE_URL}/scenarios/simulate",
            json={"location_id": location, "scenario_type": scenario_type, "value": value},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
