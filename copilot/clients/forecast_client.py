from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
FORECAST_ENGINE_URL = os.environ.get("FORECAST_ENGINE_URL", "http://localhost:8006").rstrip(
    "/"
)
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "30"))


class ForecastUnavailableError(RuntimeError):
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _extract_series(payload: dict[str, Any]) -> list[list[float]]:
    raw = payload.get("values", payload.get("predictions", []))
    series: list[list[float]] = []
    for row in list(raw):
        if isinstance(row, (list, tuple)):
            series.append([float(x) for x in row])
        else:
            series.append([float(row)])
    return series


class ForecastClient:
    def predict(
        self,
        location: str,
        days: int = 3,
        model: str = "ensemble",
        timeout: float = CLIENT_TIMEOUT,
    ) -> list[list[float]]:
        gateway_body = {
            "location_id": location,
            "target_variable": "temperature_2m",
            "horizon_hours": max(24, days * 24),
            "model_id": model,
        }
        try:
            resp = requests.post(
                f"{GATEWAY_URL}/forecast/predict",
                json=gateway_body,
                timeout=timeout,
            )
        except requests.RequestException:
            resp = None
        if resp is not None:
            if resp.status_code == 503:
                detail = resp.json().get("detail", {})
                raise ForecastUnavailableError(
                    str(detail.get("message", "Forecast unavailable")),
                    str(detail.get("error_code", "MODEL_UNAVAILABLE")),
                )
            if resp.ok:
                return _extract_series(resp.json())

        try:
            sidecar = requests.post(
                f"{FORECAST_ENGINE_URL}/forecast/predict",
                json={"location_id": location, "horizon": days, "model": model},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ForecastUnavailableError(str(exc), "FORECAST_UNREACHABLE") from exc
        if sidecar.status_code == 503:
            detail = sidecar.json().get("detail", {})
            raise ForecastUnavailableError(
                str(detail.get("message", "Forecast unavailable")),
                str(detail.get("error_code", "MODEL_UNAVAILABLE")),
            )
        sidecar.raise_for_status()
        return _extract_series(sidecar.json())
