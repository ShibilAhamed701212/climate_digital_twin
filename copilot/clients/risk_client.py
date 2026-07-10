from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

RISK_SERVICE_URL = os.environ.get("RISK_SERVICE_URL", "http://risk-engine:8003")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


class RiskClient:
    def assess(
        self,
        location: str,
        use_model_shap: bool = True,
        timeout: float = CLIENT_TIMEOUT,
    ) -> dict[str, Any]:
        resp = requests.post(
            f"{RISK_SERVICE_URL}/risk/assess",
            json={"location_id": location, "use_model_shap": use_model_shap},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["scores"]
