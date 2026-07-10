"""API client service — fetches data from the Digital Twin microservices."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

from dashboard.config.config import SAMPLE_LOCATIONS

logger = logging.getLogger(__name__)

# Endpoint URL patterns (no trailing slash)
TWIN_STATE_URL = "http://twin-state-mgr:8001"
FORECAST_ENGINE_URL = "http://forecast-engine:8006"
SCENARIO_ENGINE_URL = "http://scenario-engine:8002"
RISK_ASSESSMENT_URL = "http://risk-engine:8003"

# Predefined scenario library for offline/fallback use
PREDEFINED_SCENARIOS = [
    {
        "id": "temp_plus_1",
        "name": "Temperature +1°C",
        "description": "Global temp increases by 1°C",
    },
    {
        "id": "temp_plus_2",
        "name": "Temperature +2°C",
        "description": "Global temp increases by 2°C",
    },
    {
        "id": "temp_plus_4",
        "name": "Temperature +4°C",
        "description": "Global temp increases by 4°C",
    },
    {
        "id": "rain_plus_20",
        "name": "Rainfall +20%",
        "description": "Annual rainfall increases by 20%",
    },
    {
        "id": "rain_plus_40",
        "name": "Rainfall +40%",
        "description": "Annual rainfall increases by 40%",
    },
    {
        "id": "rain_minus_25",
        "name": "Rainfall -25%",
        "description": "Annual rainfall decreases by 25%",
    },
    {"id": "heatwave", "name": "Heatwave Event", "description": "Extreme heatwave scenario"},
    {"id": "flood", "name": "Flood Event", "description": "Extreme flooding scenario"},
]


def _synthetic_forecast(location_id: str, horizon: int) -> list[dict[str, Any]]:
    """Generate plausible synthetic forecast data."""
    from dashboard.config.config import SAMPLE_LOCATIONS

    meta = next(
        (loc for loc in SAMPLE_LOCATIONS if loc["id"] == location_id),
        {"lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
    )
    results = []
    for i in range(horizon):
        results.append(
            {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "district": meta["district"],
                "timestamp": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                "rainfall": round(10 - i * 2 + (i % 3) * 5, 1),
                "max_temp": round(32 + (i % 2) * 2, 1),
                "min_temp": round(22 - (i % 3), 1),
                "prediction_confidence": round(max(0.3, 0.85 - (i * 0.05)), 2),
                "state_type": "forecast",
                "data_source": "synthetic",
            }
        )
    return results


def _synthetic_current_state(location_id: str) -> dict[str, Any]:
    """Generate plausible synthetic current state data."""
    from dashboard.config.config import SAMPLE_LOCATIONS

    meta = next(
        (loc for loc in SAMPLE_LOCATIONS if loc["id"] == location_id),
        {"lat": 12.97, "lon": 77.59, "district": "Bengaluru Urban"},
    )
    return {
        "location_id": location_id,
        "latitude": meta["lat"],
        "longitude": meta["lon"],
        "district": meta["district"],
        "timestamp": datetime.now().isoformat(),
        "rainfall": 22.5,
        "max_temp": 32.0,
        "min_temp": 21.5,
        "risk_score": 15.0,
        "prediction_confidence": 0.75,
        "state_type": "current",
        "data_source": "synthetic",
    }


def _synthetic_risk(location_id: str) -> dict[str, Any]:
    """Generate plausible synthetic risk assessment."""
    from dashboard.config.config import SAMPLE_LOCATIONS

    meta = next(
        (loc for loc in SAMPLE_LOCATIONS if loc["id"] == location_id),
        {"district": "unknown"},
    )
    composite = 25.0
    return {
        "location_id": location_id,
        "latitude": meta["lat"],
        "longitude": meta["lon"],
        "district": meta["district"],
        "composite_risk": composite,
        "heat_risk": 32.0,
        "flood_risk": 18.0,
        "drought_risk": 14.0,
        "category": "Moderate",
        "trend": [composite],
        "shap_summary": {
            "Rainfall": round(composite * 0.02, 3),
            "MaxTemp": round(composite * 0.03, 3),
            "MinTemp": round(composite * 0.01, 3),
        },
    }


def _synthetic_scenario_result(scenario_id: str, location_id: str) -> dict[str, Any]:
    """Generate plausible synthetic scenario simulation result."""
    return {
        "status": "success",
        "data": {
            "location_id": location_id,
            "timestamp": datetime.now().isoformat(),
            "rainfall": 25.0,
            "max_temp": 34.0,
            "min_temp": 22.0,
            "state_type": "scenario",
            "scenario_id": scenario_id,
        },
    }


class DashboardAPI:
    """Client for the Digital Twin microservices."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = base_url or "http://twin-state-mgr:8001/api/v1"
        self.timeout = timeout or 10
        self._session = requests.Session()
        self._fallback_endpoints: dict[str, bool] = {}

    def _mark_fallback(self, endpoint: str, triggered: bool = True) -> None:
        if triggered:
            self._fallback_endpoints[endpoint] = True
        else:
            self._fallback_endpoints.pop(endpoint, None)

    def get_fallback_status(self) -> dict[str, bool]:
        """Return which endpoints are using fallback data."""
        return dict(self._fallback_endpoints)

    def clear_fallback_status(self) -> None:
        """Clear all fallback tracking."""
        self._fallback_endpoints.clear()

    def _location_meta(self, location_id: str) -> dict[str, Any]:
        return next(
            (loc for loc in SAMPLE_LOCATIONS if loc["id"] == location_id),
            SAMPLE_LOCATIONS[0],
        )

    # ------------------------------------------------------------------
    # Current State
    # ------------------------------------------------------------------
    def get_current_state(self, location_id: str) -> dict[str, Any] | None:
        """Get current climate state for a location."""
        meta = self._location_meta(location_id)
        try:
            resp = self._session.get(
                f"{self.base_url}/state/current",
                params={"location_id": location_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", payload)
            self._mark_fallback("current_state", False)
            return {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "district": meta["district"],
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "rainfall": data.get("rainfall", 0),
                "max_temp": data.get("max_temp", 0),
                "min_temp": data.get("min_temp", 0),
                "risk_score": data.get("risk_score", 0),
                "prediction_confidence": data.get("prediction_confidence", 0.5),
                "state_type": "current",
                "data_source": data.get("data_source", "api"),
            }
        except Exception as e:
            logger.warning("Twin service unavailable: %s", e)
            self._mark_fallback("current_state")
            return _synthetic_current_state(location_id)

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------
    def get_forecast(self, location_id: str, horizon: int = 3) -> list[dict[str, Any]]:
        """Get climate forecast for a location."""
        meta = self._location_meta(location_id)
        try:
            resp = self._session.get(
                f"{self.base_url}/forecast",
                params={"location_id": location_id, "horizon": horizon},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            entries = payload.get("data", payload) if isinstance(payload, dict) else payload
            self._mark_fallback("forecast", False)
            results = []
            for i, entry in enumerate(entries):
                rainfall = entry.get("rainfall", 0)
                max_temp = entry.get("max_temp", 0)
                min_temp = entry.get("min_temp", 0)
                results.append(
                    {
                        "location_id": location_id,
                        "latitude": meta["lat"],
                        "longitude": meta["lon"],
                        "district": meta["district"],
                        "timestamp": entry.get(
                            "timestamp",
                            (datetime.now() + timedelta(days=i + 1)).isoformat(),
                        ),
                        "rainfall": round(float(rainfall), 2),
                        "max_temp": round(float(max_temp), 2),
                        "min_temp": round(float(min_temp), 2),
                        "prediction_confidence": round(
                            float(entry.get("prediction_confidence", max(0.3, 0.85 - (i * 0.05)))),
                            2,
                        ),
                        "state_type": "forecast",
                        "data_source": entry.get("data_source", "api"),
                    }
                )
            return results
        except Exception as e:
            logger.warning("Forecast service unavailable: %s", e)
            self._mark_fallback("forecast")
            return _synthetic_forecast(location_id, horizon)

    # ------------------------------------------------------------------
    # Historical
    # ------------------------------------------------------------------
    def get_historical(self, location_id: str) -> list[dict[str, Any]]:
        """Get historical state data from the twin history."""
        try:
            resp = self._session.get(
                f"{self.base_url}/state/history",
                params={"location_id": location_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            states = resp.json()
            if not states:
                return []
            self._mark_fallback("historical", False)
            return [
                {
                    "location_id": s.get("location_id", location_id),
                    "timestamp": s.get("timestamp", ""),
                    "rainfall": s.get("rainfall", 0),
                    "max_temp": s.get("max_temp", 0),
                    "min_temp": s.get("min_temp", 0),
                    "state_type": "historical",
                }
                for s in states[-90:]
            ]
        except Exception as e:
            logger.warning("History unavailable: %s", e)
            self._mark_fallback("historical")
            return []

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------
    def get_scenarios(self) -> list[dict[str, Any]]:
        """Get list of available scenarios."""
        try:
            resp = self._session.get(f"{SCENARIO_ENGINE_URL}/scenarios", timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            self._mark_fallback("scenarios_list", False)
            return data if isinstance(data, list) else PREDEFINED_SCENARIOS
        except Exception as e:
            logger.warning("Scenario list unavailable: %s", e)
            self._mark_fallback("scenarios_list")
            return PREDEFINED_SCENARIOS

    def simulate_scenario(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Run a scenario simulation."""
        location_id = params.get("location_id", SAMPLE_LOCATIONS[0]["id"])
        scenario_id = params.get("scenario_id", "temp_plus_2")
        try:
            resp = self._session.post(
                f"{SCENARIO_ENGINE_URL}/scenarios/simulate",
                json={"scenario_id": scenario_id, "location_ids": [location_id]},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = resp.json()
            results_list = result.get("results", [])
            self._mark_fallback("scenario_simulation", False)
            if results_list:
                sim = results_list[0].get("simulated", {})
                return {
                    "status": "success",
                    "data": {
                        "location_id": location_id,
                        "timestamp": result.get("completed_at", datetime.now().isoformat()),
                        "rainfall": sim.get("rainfall", 0),
                        "max_temp": sim.get("max_temp", 0),
                        "min_temp": sim.get("min_temp", 0),
                        "state_type": "scenario",
                        "scenario_id": scenario_id,
                    },
                }
            return {"status": "success", "data": {}}
        except Exception as e:
            logger.warning("Scenario simulation unavailable: %s", e)
            self._mark_fallback("scenario_simulation")
            return _synthetic_scenario_result(scenario_id, location_id)

    # ------------------------------------------------------------------
    # Monte Carlo Simulation (via FastAPI gateway)
    # ------------------------------------------------------------------
    def run_monte_carlo(
        self,
        scenario_type: str = "temperature",
        base_params: dict[str, Any] | None = None,
        num_simulations: int = 1000,
        confidence_level: float = 0.95,
    ) -> dict[str, Any] | None:
        try:
            resp = self._session.post(
                f"{self.base_url}/scenario/monte-carlo-sim",
                json={
                    "scenario_type": scenario_type,
                    "base_params": base_params or {},
                    "num_simulations": num_simulations,
                    "confidence_level": confidence_level,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._mark_fallback("monte_carlo", False)
            return resp.json()
        except Exception as e:
            logger.warning("Monte Carlo simulation unavailable: %s", e)
            self._mark_fallback("monte_carlo")
            return None

    # ------------------------------------------------------------------
    # Scenario Comparison (via FastAPI gateway)
    # ------------------------------------------------------------------
    def compare_scenarios(
        self,
        scenarios: list[dict[str, Any]],
        baseline_index: int = 0,
    ) -> dict[str, Any] | None:
        try:
            resp = self._session.post(
                f"{self.base_url}/scenario/compare-scenarios",
                json={"scenarios": scenarios, "baseline_index": baseline_index},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._mark_fallback("compare_scenarios", False)
            return resp.json()
        except Exception as e:
            logger.warning("Scenario comparison unavailable: %s", e)
            self._mark_fallback("compare_scenarios")
            return None

    # ------------------------------------------------------------------
    # Ensemble Simulation (via FastAPI gateway)
    # ------------------------------------------------------------------
    def run_ensemble(
        self,
        members: list[dict[str, Any]],
        location_id: str = "unknown",
    ) -> dict[str, Any] | None:
        try:
            resp = self._session.post(
                f"{self.base_url}/scenario/ensemble",
                json={"members": members, "location_id": location_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._mark_fallback("ensemble", False)
            return resp.json()
        except Exception as e:
            logger.warning("Ensemble simulation unavailable: %s", e)
            self._mark_fallback("ensemble")
            return None

    # ------------------------------------------------------------------
    # Scenario Generator (via FastAPI gateway)
    # ------------------------------------------------------------------
    def generate_scenario(
        self,
        scenario_type: str,
        location_id: str,
        latitude: float,
        longitude: float,
        duration_days: int = 30,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        try:
            resp = self._session.post(
                f"{self.base_url}/scenario/scenario-generator",
                json={
                    "scenario_type": scenario_type,
                    "location_id": location_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "duration_days": duration_days,
                    "parameters": parameters or {},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            self._mark_fallback("generate_scenario", False)
            return resp.json()
        except Exception as e:
            logger.warning("Scenario generation unavailable: %s", e)
            self._mark_fallback("generate_scenario")
            return None

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------
    def get_risk(self, location_id: str) -> dict[str, Any] | None:
        """Get climate risk assessment for a location."""
        meta = self._location_meta(location_id)
        try:
            resp = self._session.get(
                f"{RISK_ASSESSMENT_URL}/risk/assess",
                params={"location_id": location_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            scores = data if isinstance(data, dict) else {}
            composite = scores.get("composite", scores.get("composite_risk", 0))
            self._mark_fallback("risk", False)
            return {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "district": meta["district"],
                "composite_risk": composite,
                "heat_risk": scores.get("heat", scores.get("heat_risk", 0)),
                "flood_risk": scores.get("flood", scores.get("flood_risk", 0)),
                "drought_risk": scores.get("drought", scores.get("drought_risk", 0)),
                "category": scores.get("category", "Low"),
                "trend": [composite],
                "shap_summary": {
                    "Rainfall": round(float(composite) * 0.02, 3),
                    "MaxTemp": round(float(composite) * 0.03, 3),
                    "MinTemp": round(float(composite) * 0.01, 3),
                },
            }
        except Exception as e:
            logger.warning("Risk service unavailable: %s", e)
            self._mark_fallback("risk")
            return _synthetic_risk(location_id)

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------
    def get_all_locations(self) -> list[dict[str, Any]]:
        """Return all sample locations."""
        return SAMPLE_LOCATIONS

    # ------------------------------------------------------------------
    # District Summary
    # ------------------------------------------------------------------
    def get_district_summary(self, district: str) -> dict[str, Any]:
        """Get a summary for a specific district."""
        locs = [loc for loc in SAMPLE_LOCATIONS if loc["district"] == district]
        if not locs:
            return {
                "district": district,
                "rainy_days": 0,
                "extreme_heat_days": 0,
                "error": "District not found",
            }
        loc = locs[0]
        state = self.get_current_state(loc["id"])
        risk = self.get_risk(loc["id"])
        if state:
            risk_level = "Moderate"
            if risk:
                comp = risk.get("composite_risk", 0)
                if comp < 25:
                    risk_level = "Low"
                elif comp < 50:
                    risk_level = "Moderate"
                elif comp < 75:
                    risk_level = "High"
                else:
                    risk_level = "Severe"
            return {
                "district": district,
                "avg_max_temp": state.get("max_temp", 0),
                "avg_min_temp": state.get("min_temp", 0),
                "total_rainfall_ytd": state.get("rainfall", 0),
                "rainy_days": 60,
                "extreme_heat_days": 10,
                "risk_level": risk_level,
            }
        return {
            "district": district,
            "rainy_days": 0,
            "extreme_heat_days": 0,
            "error": "No data available",
        }


def create_api_client() -> DashboardAPI:
    return DashboardAPI()
