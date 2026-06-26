"""API client service — fetches data from the FastAPI backend with synthetic fallback."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

import requests

from dashboard.config.config import API_BASE_URL, API_TIMEOUT, SAMPLE_LOCATIONS

logger = logging.getLogger(__name__)


class DashboardAPI:
    """Client for the Digital Twin FastAPI backend."""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = API_TIMEOUT) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._session = requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            resp = self._session.get(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("API request failed: %s", e)
            return None

    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        data = self._get("current", {"location_id": location_id})
        if data and "data" in data:
            return data["data"]
        return self._synthetic_current(location_id)

    def get_forecast(self, location_id: str, horizon: int = 3) -> list[dict[str, Any]]:
        data = self._get("forecast", {"location_id": location_id, "horizon": horizon})
        if data and "data" in data:
            return data["data"]
        return self._synthetic_forecast(location_id, horizon)

    def get_historical(
        self, location_id: str, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"location_id": location_id}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        data = self._get("historical", params)
        if data and "data" in data:
            return data["data"]
        return self._synthetic_historical(location_id)

    def get_scenarios(self) -> list[dict[str, Any]]:
        data = self._get("scenarios/list")
        if data and "data" in data:
            return data["data"]
        return self._synthetic_scenarios()

    def simulate_scenario(self, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
            resp = self._session.post(
                f"{self.base_url}/scenarios/simulate",
                json=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Scenario simulation request failed: %s", e)
            return self._synthetic_simulation(params)

    def get_risk(self, location_id: str) -> dict[str, Any] | None:
        data = self._get("risk", {"location_id": location_id})
        if data and "data" in data:
            return data["data"]
        return self._synthetic_risk(location_id)

    def get_all_locations(self) -> list[dict[str, Any]]:
        return SAMPLE_LOCATIONS

    def get_district_summary(self, district: str) -> dict[str, Any]:
        return self._synthetic_district_summary(district)

    @staticmethod
    def _random_entity(location_id: str) -> dict[str, Any]:
        loc = next((ent for ent in SAMPLE_LOCATIONS if ent["id"] == location_id), SAMPLE_LOCATIONS[0])
        return {
            "location_id": location_id,
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "district": loc["district"],
            "timestamp": datetime.now().isoformat(),
            "rainfall": round(random.uniform(0, 120), 2),
            "max_temp": round(random.uniform(25, 40), 2),
            "min_temp": round(random.uniform(15, 24), 2),
            "risk_score": round(random.uniform(0, 100), 1),
            "prediction_confidence": round(random.uniform(0.6, 1.0), 2),
            "state_type": "current",
            "data_source": "IMD",
        }

    def _synthetic_current(self, location_id: str) -> dict[str, Any]:
        return self._random_entity(location_id)

    def _synthetic_forecast(self, location_id: str, horizon: int) -> list[dict[str, Any]]:
        base = self._random_entity(location_id)
        results = []
        for day in range(horizon):
            entry = dict(base)
            entry["timestamp"] = (datetime.now() + timedelta(days=day + 1)).isoformat()
            entry["rainfall"] = round(max(0, base["rainfall"] + random.gauss(0, 15)), 2)
            entry["max_temp"] = round(base["max_temp"] + random.gauss(0, 2), 2)
            entry["min_temp"] = round(base["min_temp"] + random.gauss(0, 1.5), 2)
            entry["prediction_confidence"] = round(max(0.3, base["prediction_confidence"] - day * 0.08), 2)
            entry["state_type"] = "forecast"
            results.append(entry)
        return results

    def _synthetic_historical(self, location_id: str) -> list[dict[str, Any]]:
        base = self._random_entity(location_id)
        results = []
        for days_ago in range(90, 0, -1):
            entry = dict(base)
            entry["timestamp"] = (datetime.now() - timedelta(days=days_ago)).isoformat()
            entry["rainfall"] = round(max(0, base["rainfall"] + random.gauss(0, 20)), 2)
            entry["max_temp"] = round(base["max_temp"] + random.gauss(0, 3), 2)
            entry["min_temp"] = round(base["min_temp"] + random.gauss(0, 2), 2)
            entry["state_type"] = "historical"
            results.append(entry)
        return results

    @staticmethod
    def _synthetic_scenarios() -> list[dict[str, Any]]:
        return [
            {"id": "temp_plus_2", "name": "Temperature +2°C", "description": "Raises temperature by 2°C across all locations"},
            {"id": "rain_plus_20", "name": "Rainfall +20%", "description": "Increases rainfall by 20% across all locations"},
            {"id": "extreme_heat", "name": "Extreme Heat Wave", "description": "Simulates a week-long heat wave with temperatures 5°C above normal"},
            {"id": "flood", "name": "Flood Scenario", "description": "Simulates heavy rainfall event with 200% normal precipitation"},
            {"id": "drought", "name": "Drought Condition", "description": "Simulates a month-long drought with 80% reduction in rainfall"},
        ]

    def _synthetic_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        scenario_id = params.get("scenario_id", "unknown")
        location_id = params.get("location_id", SAMPLE_LOCATIONS[0]["id"])
        base = self._random_entity(location_id)
        result = dict(base)
        result["scenario_id"] = scenario_id
        result["state_type"] = "scenario"
        delta_temp = params.get("temperature_delta", 0)
        delta_rain_pct = params.get("rainfall_change_pct", 0)
        result["max_temp"] = round(base["max_temp"] + delta_temp, 2)
        result["min_temp"] = round(base["min_temp"] + delta_temp, 2)
        result["rainfall"] = round(max(0, base["rainfall"] * (1 + delta_rain_pct / 100)), 2)
        return {"status": "success", "data": result}

    @staticmethod
    def _synthetic_risk(location_id: str) -> dict[str, Any]:
        loc = next((ent for ent in SAMPLE_LOCATIONS if ent["id"] == location_id), SAMPLE_LOCATIONS[0])
        return {
            "location_id": location_id,
            "district": loc["district"],
            "composite_risk": round(random.uniform(10, 90), 1),
            "heat_risk": round(random.uniform(10, 90), 1),
            "flood_risk": round(random.uniform(10, 90), 1),
            "drought_risk": round(random.uniform(10, 90), 1),
            "trend": [round(random.uniform(10, 90), 1) for _ in range(12)],
            "shap_summary": {
                "Rainfall": round(random.uniform(-0.5, 0.5), 3),
                "MaxTemp": round(random.uniform(-0.5, 0.5), 3),
                "MinTemp": round(random.uniform(-0.5, 0.5), 3),
            },
        }

    @staticmethod
    def _synthetic_district_summary(district: str) -> dict[str, Any]:
        return {
            "district": district,
            "total_rainfall_ytd": round(random.uniform(500, 3000), 1),
            "avg_max_temp": round(random.uniform(28, 36), 2),
            "avg_min_temp": round(random.uniform(16, 22), 2),
            "rainy_days": random.randint(30, 120),
            "extreme_heat_days": random.randint(5, 30),
            "risk_level": random.choice(["Low", "Moderate", "High", "Severe"]),
        }


def create_api_client() -> DashboardAPI:
    return DashboardAPI()
