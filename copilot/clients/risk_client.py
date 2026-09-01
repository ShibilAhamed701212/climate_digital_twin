from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

RISK_SERVICE_URL = os.environ.get("RISK_SERVICE_URL", "http://localhost:8003")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


def _numeric_score(obj: Any) -> float | None:
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        for key in ("score", "composite_score", "value"):
            if key in obj and isinstance(obj[key], (int, float)):
                return float(obj[key])
    return None


def flatten_risk_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map nested RiskReport.to_dict() into the copilot score contract."""
    if isinstance(payload.get("scores"), dict):
        scores = dict(payload["scores"])
        if all(k in scores for k in ("heat", "flood", "drought", "composite")):
            return scores

    heat = _numeric_score(payload.get("heat_risk"))
    flood = _numeric_score(payload.get("flood_risk") or payload.get("heavy_rain_risk"))
    drought = _numeric_score(payload.get("drought_risk") or payload.get("dryness_risk"))
    composite_obj = payload.get("composite_risk")
    composite = _numeric_score(composite_obj)
    category = None
    if isinstance(composite_obj, dict):
        category = composite_obj.get("category")
    if category is None:
        category = payload.get("category")

    flattened = {
        "heat": heat,
        "flood": flood,
        "drought": drought,
        "composite": composite,
        "category": category,
    }
    return flattened


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
        payload = resp.json()
        return flatten_risk_payload(payload)
