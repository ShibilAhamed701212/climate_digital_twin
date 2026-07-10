from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

FORECAST_SERVICE_URL = os.environ.get("FORECAST_SERVICE_URL", "http://forecast-engine:8006")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


class ForecastClient:
    def predict(
        self,
        location: str,
        days: int = 3,
        model: str = "ensemble",
        timeout: float = CLIENT_TIMEOUT,
    ) -> list[list[float]]:
        resp = requests.post(
            f"{FORECAST_SERVICE_URL}/forecast/predict",
            json={"location_id": location, "horizon": days, "model": model},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["predictions"]
