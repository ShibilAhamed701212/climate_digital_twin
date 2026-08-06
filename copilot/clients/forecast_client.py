from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "30"))


class ForecastUnavailableError(RuntimeError):
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class ForecastClient:
    def predict(
        self,
        location: str,
        days: int = 3,
        model: str = "ensemble",
        timeout: float = CLIENT_TIMEOUT,
    ) -> list[list[float]]:
        try:
            resp = requests.post(
                f"{GATEWAY_URL}/forecast/predict",
                json={
                    "location_id": location,
                    "target_variable": "temperature_2m",
                    "horizon_hours": max(24, days * 24),
                    "model_id": model,
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ForecastUnavailableError(str(exc), "GATEWAY_UNREACHABLE") from exc
        if resp.status_code == 503:
            detail = resp.json().get("detail", {})
            raise ForecastUnavailableError(
                str(detail.get("message", "Forecast unavailable")),
                str(detail.get("error_code", "MODEL_UNAVAILABLE")),
            )
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        return list(payload.get("values", []))
