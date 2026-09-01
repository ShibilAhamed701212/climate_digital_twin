"""API client service — fetches data from the Digital Twin gateway."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests

from dashboard.config.config import SAMPLE_LOCATIONS
from pipeline.providers.historical_store import HistoricalStore
from pipeline.providers.manager import DataSourceManager, ObservationStatus

# WMO weather code -> human-readable label
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


logger = logging.getLogger(__name__)

# Phase 6: the dashboard talks ONLY to the gateway (:8000). The stale
# twin-state-mgr/forecast-engine/risk-engine endpoints are gone.
GATEWAY_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")


class DashboardAPI:
    """Client for the Digital Twin gateway."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or GATEWAY_URL).rstrip("/")
        self.timeout = timeout or 10
        self._session = requests.Session()
        self._fallback_endpoints: dict[str, bool] = {}
        _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _data_dir = os.path.join(_project_root, "data", "raw")
        self._dsm = DataSourceManager(config={"historical": {"data_dir": _data_dir}})
        self._dsm._historical_store = HistoricalStore(data_dir=_data_dir)

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
        """Get current climate state for a location (gateway, authoritative twin)."""
        meta = self._location_meta(location_id)
        try:
            resp = self._session.get(
                f"{self.base_url}/twin/state/{location_id}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            self._mark_fallback("current_state", False)
            rainfall = data.get("rainfall", data.get("precipitation_mm", 0))
            max_temp = data.get("max_temp") or data.get("temperature_2m")
            min_temp = (
                data.get("min_temp") or data.get("temperature_2m_min") or data.get("temperature_2m")
            )
            result = {
                "location_id": location_id,
                "latitude": float(data.get("latitude", meta["lat"])),
                "longitude": float(data.get("longitude", meta["lon"])),
                "district": data.get("district", meta["district"]),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "rainfall": float(rainfall),
                "current_temp": float(data.get("temperature_2m", 0)),
                "humidity_pct": data.get("humidity_pct"),
                "pressure_hpa": data.get("pressure_hpa"),
                "wind_speed_10m": data.get("wind_speed_10m"),
                "max_temp": max_temp,
                "min_temp": min_temp,
                "risk_score": data.get("risk_score"),
                "prediction_confidence": float(data.get("prediction_confidence") or 0.0),
                "state_type": "current",
                "data_source": data.get("data_source", "twin"),
                "quality_flag": data.get("quality_flag", ""),
            }
            # The twin schema is frozen at 5 fields, so daily max/min are
            # filled from live extended conditions when absent.
            if result["max_temp"] is None or result["min_temp"] is None:
                ext = self.get_extended_conditions(location_id)
                if ext.get("status") != "unavailable":
                    result["max_temp"] = result["max_temp"] or ext.get("daily_max_temp")
                    result["min_temp"] = result["min_temp"] or ext.get("daily_min_temp")
            return result
        except Exception as e:
            logger.warning("Gateway twin state unavailable: %s", e)
            self._mark_fallback("current_state")
            try:
                twin_url = os.environ.get("TWIN_STATE_URL", "http://localhost:8001")
                twin_resp = self._session.get(
                    f"{twin_url}/state/current",
                    params={"location_id": location_id},
                    timeout=self.timeout,
                )
                twin_resp.raise_for_status()
                data = twin_resp.json()
                return {
                    "location_id": location_id,
                    "latitude": meta["lat"],
                    "longitude": meta["lon"],
                    "district": meta["district"],
                    "timestamp": data.get("timestamp", datetime.now().isoformat()),
                    "rainfall": float(data.get("rainfall", 0)),
                    "current_temp": float(data.get("max_temp", 0)),
                    "max_temp": data.get("max_temp"),
                    "min_temp": data.get("min_temp"),
                    "humidity_pct": data.get("humidity_pct"),
                    "pressure_hpa": data.get("pressure_hpa"),
                    "wind_speed_10m": data.get("wind_speed_10m"),
                    "risk_score": None,
                    "prediction_confidence": 0.0,
                    "state_type": "current",
                    "data_source": data.get("data_source", "twin-state-mgr"),
                    "quality_flag": data.get("quality_flag", ""),
                }
            except Exception:
                pass
            # Fetch all three variables separately so we get real values
            obs_temp = self._dsm.get_observation(location_id, "temperature_2m")
            obs_min = self._dsm.get_observation(location_id, "temperature_2m_min")
            obs_rain = self._dsm.get_observation(location_id, "precipitation_mm")
            has_data = any(
                o.status != ObservationStatus.UNAVAILABLE for o in (obs_temp, obs_min, obs_rain)
            )
            if has_data:
                max_temp = obs_temp.values.get("temperature_2m", 0)
                min_temp_obs = obs_min.values.get("temperature_2m_min", 0)
                rainfall = obs_rain.values.get("precipitation_mm", 0)
                best_obs = next(
                    (
                        o
                        for o in (obs_temp, obs_min, obs_rain)
                        if o.status != ObservationStatus.UNAVAILABLE
                    ),
                    obs_temp,
                )
                return {
                    "location_id": location_id,
                    "latitude": meta["lat"],
                    "longitude": meta["lon"],
                    "district": meta["district"],
                    "timestamp": best_obs.observation_timestamp or datetime.now().isoformat(),
                    "rainfall": rainfall,
                    "current_temp": max_temp,
                    "max_temp": max_temp,
                    "min_temp": min_temp_obs,
                    "risk_score": None,
                    "prediction_confidence": best_obs.confidence,
                    "state_type": "current",
                    "data_source": best_obs.status.value,
                    "provider": best_obs.provider,
                    "dataset_version": best_obs.dataset_version,
                }
            return {
                "status": "unavailable",
                "message": "No verified climate observations available.",
                "location_id": location_id,
                "rainfall": 0.0,
                "max_temp": None,
                "min_temp": None,
                "current_temp": None,
            }

    # ------------------------------------------------------------------
    # Extended Live Conditions (direct from Open-Meteo)
    # ------------------------------------------------------------------
    _extended_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _EXTENDED_TTL_SECONDS = 300

    @classmethod
    def _extended_weather_code(cls, code: Any) -> str:
        try:
            return WMO_CODES.get(int(code), f"Code {code}")
        except (TypeError, ValueError):
            return "Unavailable"

    def get_extended_conditions(self, location_id: str) -> dict[str, Any]:
        """Get extended live conditions straight from Open-Meteo.

        Covers apparent temperature, daily max/min, wind gusts, weather
        code, precipitation probability, UV index and sunrise/sunset. The
        twin-state schema is frozen at 5 fields, so these are pulled live
        and cached briefly instead of persisted.
        """
        meta = self._location_meta(location_id)
        now = time.time()
        cached = self._extended_cache.get(location_id)
        if cached and now - cached[0] < self._EXTENDED_TTL_SECONDS:
            return cached[1]
        try:
            resp = self._session.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": meta["lat"],
                    "longitude": meta["lon"],
                    "current": (
                        "temperature_2m,apparent_temperature,relative_humidity_2m,"
                        "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
                        "pressure_msl,precipitation_probability,uv_index"
                    ),
                    "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
                    "timezone": "auto",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            current = payload.get("current", {})
            daily = payload.get("daily", {})
            result = {
                "location_id": location_id,
                "apparent_temperature": current.get("apparent_temperature"),
                "weather_code": self._extended_weather_code(current.get("weather_code")),
                "wind_gusts_10m": current.get("wind_gusts_10m"),
                "precipitation_probability": current.get("precipitation_probability"),
                "uv_index": current.get("uv_index"),
                "daily_max_temp": (daily.get("temperature_2m_max") or [None])[0],
                "daily_min_temp": (daily.get("temperature_2m_min") or [None])[0],
                "sunrise": (daily.get("sunrise") or [None])[0],
                "sunset": (daily.get("sunset") or [None])[0],
                "timestamp": current.get("time"),
                "data_source": "open_meteo",
            }
            self._extended_cache[location_id] = (now, result)
            return result
        except Exception as e:
            logger.warning("Extended live conditions unavailable for %s: %s", location_id, e)
            return {"location_id": location_id, "status": "unavailable"}

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------
    def get_forecast(self, location_id: str, horizon: int = 3) -> list[dict[str, Any]]:
        """Get climate forecast via the gateway."""
        meta = self._location_meta(location_id)
        try:
            resp = self._session.post(
                f"{self.base_url}/forecast/predict",
                json={
                    "location_id": location_id,
                    "target_variable": "temperature_2m",
                    "horizon_hours": max(24, int(horizon) * 24),
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            self._mark_fallback("forecast", False)

            timestamps = payload.get("timestamps", [])
            values = payload.get("values", [])
            confidence = float(payload.get("confidence", 0.0) or 0.0)
            results = []
            for i, day in enumerate(values):
                if not isinstance(day, list | tuple):
                    day = [day]
                results.append(
                    {
                        "location_id": location_id,
                        "latitude": meta["lat"],
                        "longitude": meta["lon"],
                        "district": meta["district"],
                        "timestamp": (
                            timestamps[i]
                            if i < len(timestamps)
                            else (datetime.now() + timedelta(days=i + 1)).isoformat()
                        ),
                        "rainfall": round(float(day[0]) if len(day) > 0 else 0.0, 2),
                        "max_temp": round(float(day[1]) if len(day) > 1 else 0.0, 2),
                        "min_temp": round(float(day[2]) if len(day) > 2 else 0.0, 2),
                        "prediction_confidence": round(confidence, 2),
                        "state_type": "forecast",
                        "data_source": payload.get("authenticity", "MODEL"),
                        "model_id": payload.get("model_id", ""),
                        "forecast_id": payload.get("forecast_id", ""),
                    }
                )
            return results
        except Exception as e:
            logger.warning("Forecast unavailable via gateway: %s", e)
            self._mark_fallback("forecast")
            engine_url = os.environ.get(
                "FORECAST_ENGINE_URL", "http://localhost:8006"
            ).rstrip("/")
            try:
                sidecar = self._session.post(
                    f"{engine_url}/forecast/predict",
                    json={"location_id": location_id, "horizon": int(horizon)},
                    timeout=self.timeout,
                )
                sidecar.raise_for_status()
                payload = sidecar.json()
                values = payload.get("predictions", payload.get("values", []))
                results = []
                for i, day in enumerate(values):
                    if not isinstance(day, (list, tuple)):
                        day = [day]
                    results.append(
                        {
                            "location_id": location_id,
                            "latitude": meta["lat"],
                            "longitude": meta["lon"],
                            "district": meta["district"],
                            "timestamp": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                            "rainfall": round(float(day[0]) if len(day) > 0 else 0.0, 2),
                            "max_temp": round(float(day[1]) if len(day) > 1 else float(day[0]), 2),
                            "min_temp": round(
                                float(day[2]) if len(day) > 2 else float(day[0] if day else 0.0),
                                2,
                            ),
                            "prediction_confidence": 0.0,
                            "state_type": "forecast",
                            "data_source": payload.get("model", "forecast-engine"),
                            "model_id": payload.get("model", ""),
                            "forecast_id": "",
                        }
                    )
                if results:
                    return results
            except Exception as sidecar_exc:
                logger.warning("Forecast sidecar unavailable: %s", sidecar_exc)
            return []

    # ------------------------------------------------------------------
    # Historical
    # ------------------------------------------------------------------
    def get_historical(self, location_id: str) -> list[dict[str, Any]]:
        """Get historical state series from the gateway twin version history."""
        try:
            resp = self._session.get(
                f"{self.base_url}/twin/history/{location_id}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            versions = payload.get("versions", []) if isinstance(payload, dict) else []
            if not versions:
                raise ValueError("No versions in gateway response")
            self._mark_fallback("historical", False)
            series = []
            for v in versions:
                state = v.get("state")
                if not isinstance(state, dict):
                    continue
                rf = state.get("rainfall", state.get("precipitation_mm", 0))
                mx = state.get("max_temp", state.get("temperature_2m", 0))
                mn = state.get(
                    "min_temp", state.get("temperature_2m_min", state.get("temperature_2m", 0))
                )
                series.append(
                    {
                        "location_id": location_id,
                        "timestamp": state.get("timestamp", v.get("created_at", "")),
                        "rainfall": float(rf),
                        "max_temp": float(mx),
                        "min_temp": float(mn),
                        "humidity_pct": state.get("humidity_pct", 0),
                        "pressure_hpa": state.get("pressure_hpa", 0),
                        "state_type": "historical",
                        "data_source": state.get("data_source", ""),
                    }
                )
            # Gateway version history is often thin (a few snapshots).
            # When fewer than 10 versions exist, supplement with parquet
            # data which has hundreds of daily records.
            if len(series) < 10:
                local_series = self._historical_from_parquet(location_id)
                if len(local_series) > len(series):
                    return local_series[-90:]
            return series[-90:]
        except Exception as e:
            logger.warning("History unavailable from gateway: %s — trying twin sidecar", e)
            twin_url = os.environ.get("TWIN_STATE_URL", "http://localhost:8001").rstrip("/")
            try:
                twin_resp = self._session.get(
                    f"{twin_url}/state/history",
                    params={"location_id": location_id},
                    timeout=self.timeout,
                )
                twin_resp.raise_for_status()
                rows = twin_resp.json()
                if isinstance(rows, list) and len(rows) >= 2:
                    series = []
                    for state in rows:
                        if not isinstance(state, dict):
                            continue
                        series.append(
                            {
                                "location_id": location_id,
                                "timestamp": state.get("timestamp", ""),
                                "rainfall": float(state.get("rainfall", 0)),
                                "max_temp": float(state.get("max_temp", 0)),
                                "min_temp": float(state.get("min_temp", 0)),
                                "humidity_pct": state.get("humidity_pct", 0),
                                "pressure_hpa": state.get("pressure_hpa", 0),
                                "state_type": "historical",
                                "data_source": state.get("data_source", ""),
                            }
                        )
                    if len(series) >= 2:
                        return series[-90:]
            except Exception as sidecar_exc:
                logger.warning("Twin history sidecar unavailable: %s", sidecar_exc)
            self._mark_fallback("historical")
            return self._historical_from_parquet(location_id)

    def _historical_from_parquet(self, location_id: str) -> list[dict[str, Any]]:
        """Build a historical series from local parquet files (last 90 days of data)."""
        try:
            from pathlib import Path

            import pandas as pd

            data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
            rain_path = data_dir / "rainfall.parquet"
            max_path = data_dir / "maxtemp.parquet"
            min_path = data_dir / "mintemp.parquet"

            if not rain_path.exists():
                return []

            meta = self._location_meta(location_id)
            target_lat, target_lon = meta["lat"], meta["lon"]

            df_rain = pd.read_parquet(rain_path)
            df_max = pd.read_parquet(max_path) if max_path.exists() else None
            df_min = pd.read_parquet(min_path) if min_path.exists() else None

            lats = df_rain["Latitude"].unique()
            lons = df_rain["Longitude"].unique()
            c_lat = min(lats, key=lambda x: abs(x - target_lat))
            c_lon = min(lons, key=lambda x: abs(x - target_lon))

            sub_rain = df_rain[(df_rain["Latitude"] == c_lat) & (df_rain["Longitude"] == c_lon)]
            sub_max = (
                df_max[(df_max["Latitude"] == c_lat) & (df_max["Longitude"] == c_lon)]
                if df_max is not None
                else None
            )
            sub_min = (
                df_min[(df_min["Latitude"] == c_lat) & (df_min["Longitude"] == c_lon)]
                if df_min is not None
                else None
            )

            if sub_rain.empty:
                sub_rain = df_rain

            # Use the last 90 unique dates
            dates = sub_rain["Date"].drop_duplicates().sort_values().tail(90)

            # Build a date-indexed lookup for each variable
            rain_by_date = sub_rain.groupby("Date")["Rainfall"].first()
            max_by_date = (
                sub_max.groupby("Date")["MaxTemp"].first()
                if sub_max is not None and not sub_max.empty
                else None
            )
            min_by_date = (
                sub_min.groupby("Date")["MinTemp"].first()
                if sub_min is not None and not sub_min.empty
                else None
            )

            series: list[dict[str, Any]] = []
            for dt in dates:
                series.append(
                    {
                        "location_id": location_id,
                        "timestamp": str(dt),
                        "rainfall": round(float(rain_by_date.get(dt, 0)), 2),
                        "max_temp": round(float(max_by_date.get(dt, 0)), 2)
                        if max_by_date is not None
                        else 0,
                        "min_temp": round(float(min_by_date.get(dt, 0)), 2)
                        if min_by_date is not None
                        else 0,
                        "humidity_pct": 0,
                        "pressure_hpa": 0,
                        "state_type": "historical",
                        "data_source": "local_parquet",
                    }
                )
            return series
        except Exception as e:
            logger.warning("Local parquet historical fallback failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------
    def get_scenarios(self) -> list[dict[str, Any]]:
        """Get list of available scenarios (gateway template catalogue)."""
        try:
            resp = self._session.get(f"{self.base_url}/scenario/templates", timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
            raw = (
                payload.get("templates", payload.get("scenarios", []))
                if isinstance(payload, dict)
                else payload
            )
            templates: list[dict[str, Any]] = []
            if isinstance(raw, list):
                templates = [t for t in raw if isinstance(t, dict)]
            elif isinstance(raw, dict):
                for _category, items in raw.items():
                    if isinstance(items, list):
                        templates.extend([t for t in items if isinstance(t, dict)])
            self._mark_fallback("scenarios_list", False)
            return [
                {
                    "id": d.get("scenario_id", d.get("name", d.get("id", ""))),
                    "name": d.get("display_name", d.get("name", "Scenario")),
                    "description": d.get("description", ""),
                    "type": d.get("type", ""),
                }
                for d in templates
            ]
        except Exception as e:
            logger.warning("Scenario list unavailable: %s — using default preset scenarios", e)
            self._mark_fallback("scenarios_list")
            return [
                {
                    "id": "heatwave_2026",
                    "name": "Severe Heatwave (+3.5°C)",
                    "description": "Simulates an extreme summer heatwave event across Karnataka with a +3.5°C temperature anomaly.",
                },
                {
                    "id": "monsoon_deficit",
                    "name": "Monsoon Deficit (-40% Rain)",
                    "description": "Evaluates drought risk under a 40% reduction in seasonal monsoon precipitation.",
                },
                {
                    "id": "extreme_precipitation",
                    "name": "Flash Flood Risk (+80% Rain)",
                    "description": "Simulates intense cloudburst conditions with an 80% increase in peak 24h rainfall.",
                },
                {
                    "id": "climate_change_2030",
                    "name": "2030 Warming Scenario (+1.5°C, +15% Rain)",
                    "description": "Mid-century climate projection under moderate emissions scenario.",
                },
            ]

    def simulate_scenario(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Run a what-if scenario via the gateway (create + run).

        Never routes scenario execution through the demo :8002 service.
        """
        location_id = params.get("location_id", SAMPLE_LOCATIONS[0]["id"])
        meta = self._location_meta(location_id)
        try:
            temp_delta = float(params.get("temperature_delta") or 0.0)
            rain_change_pct = float(params.get("rainfall_change_pct") or 0.0)
            create_body = {
                "name": f"Dashboard scenario {datetime.now().isoformat(timespec='seconds')}",
                "description": "Created by the dashboard what-if simulator",
                "scenario_type": "custom",
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "duration_days": 30,
                "temperature_delta": temp_delta,
                "rainfall_multiplier": 1.0 + rain_change_pct / 100.0,
            }
            resp = self._session.post(
                f"{self.base_url}/scenario/create",
                json=create_body,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            scenario_id = resp.json().get("scenario_id", "")

            resp = self._session.post(
                f"{self.base_url}/scenario/run",
                json={"scenario_id": scenario_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = resp.json()
            scenario = result.get("scenario", {})
            self._mark_fallback("scenario_simulation", False)
            return {
                "status": "success",
                "data": {
                    "location_id": location_id,
                    "timestamp": result.get("time_steps", [datetime.now().isoformat()])[0],
                    "rainfall": scenario.get("precipitation_mm", 0),
                    "max_temp": scenario.get("temperature_2m", 0),
                    "min_temp": scenario.get("temperature_2m", 0),
                    "state_type": "scenario",
                    "scenario_id": scenario_id,
                    "authenticity": result.get("authenticity", "SCENARIO"),
                    "mode": result.get("mode", "REAL"),
                    "baseline": result.get("baseline", {}),
                    "scenario": result.get("scenario", {}),
                    "deltas": result.get("deltas", {}),
                    "baseline_hazard": result.get("baseline_hazard"),
                    "scenario_hazard": result.get("scenario_hazard"),
                },
            }
        except Exception as e:
            logger.warning("Scenario simulation unavailable: %s", e)
            self._mark_fallback("scenario_simulation")
            return {
                "status": "unavailable",
                "message": f"Scenario simulation unavailable: {e}",
            }

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
    @staticmethod
    def _meta_float(meta: dict[str, Any], key: str) -> float | None:
        raw = meta.get(key, "")
        if raw in ("", None):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def get_risk(self, location_id: str) -> dict[str, Any] | None:
        """Get climate risk assessment from the gateway."""
        meta = self._location_meta(location_id)
        state = self.get_current_state(location_id)
        if state and state.get("status") == "unavailable":
            state = None

        try:
            req_body = {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "include_explainability": True,
            }
            resp = self._session.post(
                f"{self.base_url}/risk/assess",
                json=req_body,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            self._mark_fallback("risk", False)
            if data.get("metadata", {}).get("data_quality") in {"REJECTED", "UNAVAILABLE"}:
                return None

            composite_score = float(data.get("composite_score", 0) or 0)
            scores = data.get("scores", [])
            hazard_scores: dict[str, float] = {}
            for s in scores:
                if isinstance(s, dict):
                    hazard_scores[str(s.get("hazard_type", "unknown"))] = float(
                        s.get("score", 0) or 0
                    )

            result = {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "district": meta["district"],
                "composite_risk": composite_score * 100.0,
                "heat_risk": max(hazard_scores.get("heat", 0), hazard_scores.get("heatwave", 0))
                * 100.0,
                "flood_risk": hazard_scores.get("heavy_rain", 0) * 100.0,
                "drought_risk": hazard_scores.get("dryness", 0) * 100.0,
                "category": data.get("composite_category", "Unknown"),
                "trend": [composite_score * 100.0],
                "raw_report": data,
                "data_source": "gateway_risk_service",
                "inputs": {
                    "max_temp": self._meta_float(data.get("metadata") or {}, "input_max_temp"),
                    "min_temp": self._meta_float(data.get("metadata") or {}, "input_min_temp"),
                    "rainfall": self._meta_float(data.get("metadata") or {}, "input_rainfall"),
                    "dry_period_days": self._meta_float(
                        data.get("metadata") or {}, "input_dry_period_days"
                    ),
                    "data_source": (data.get("metadata") or {}).get("input_data_source", ""),
                },
                "primary_hazard": (data.get("metadata") or {}).get("primary_hazard", ""),
            }
            # Prefer real stored hazard trend when available.
            try:
                trend_resp = self._session.get(
                    f"{self.base_url}/risk/trend/{location_id}",
                    timeout=self.timeout,
                )
                if trend_resp.status_code == 200:
                    trend_payload = trend_resp.json()
                    points = trend_payload.get("assessments", trend_payload.get("trend", []))
                    if isinstance(points, list) and points:
                        scores = []
                        for p in points:
                            if isinstance(p, dict):
                                scores.append(
                                    float(p.get("composite_score", p.get("score", 0)) or 0) * 100.0
                                )
                        if scores:
                            result["trend"] = scores[-12:]
            except requests.RequestException:
                pass
            try:
                explain = self._session.post(
                    f"{self.base_url}/risk/explain",
                    json={
                        "assessment_id": data.get("assessment_id", ""),
                        "location_id": location_id,
                        "latitude": meta["lat"],
                        "longitude": meta["lon"],
                    },
                    timeout=self.timeout,
                ).json()
                contributions = explain.get("hazard_contributions", {}).get("composite", {})
                if contributions:
                    result["shap_summary"] = contributions
                    result["explainability_method"] = "deterministic_attribution"
            except requests.RequestException:
                pass
            return result
        except Exception as e:
            logger.warning("Risk service unavailable: %s", e)
            self._mark_fallback("risk")
            rain_v = float(state.get("rainfall") or 0) if isinstance(state, dict) else 0.0
            max_temp_v = float(state.get("max_temp") or 30) if isinstance(state, dict) else 30.0
            heat_score = min(100.0, max(0.0, (max_temp_v - 30) * 5))
            flood_score = min(100.0, max(0.0, rain_v * 1.5))
            comp_score = round(heat_score * 0.4 + flood_score * 0.6, 1)
            return {
                "location_id": location_id,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "district": meta["district"],
                "timestamp": datetime.now().isoformat(),
                "composite_risk": comp_score,
                "heat_risk": round(heat_score, 1),
                "flood_risk": round(flood_score, 1),
                "drought_risk": 10.0,
                "agricultural_risk": 15.0,
                "authenticity": "FALLBACK",
            }

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------
    def get_all_locations(self) -> list[dict[str, Any]]:
        """Return all sample locations."""
        return SAMPLE_LOCATIONS

    def get_pipeline_status(self, location_id: str) -> dict[str, Any]:
        """Check whether the live provider-to-Copilot workflow is usable."""
        checks: dict[str, bool] = {}
        try:
            health = self._session.get(f"{self.base_url}/health", timeout=10).json()
            services = health.get("services", {})
            checks["gateway"] = services.get("gateway") == "healthy" or health.get("status") in {
                "healthy",
                "degraded",
            }
            checks["observation"] = services.get("gateway") == "healthy"
            checks["twin"] = services.get("twin") in {"available", "healthy"}
            checks["forecast"] = services.get("forecast") in {"available", "healthy"}
            checks["risk"] = services.get("risk") in {"available", "healthy"}
            checks["scenario"] = services.get("scenario") in {"available", "healthy"}
        except requests.RequestException:
            checks["gateway"] = False
            checks["observation"] = False
            checks["twin"] = False
            checks["forecast"] = False
            checks["risk"] = False
            checks["scenario"] = False

        state = self.get_current_state(location_id)
        checks["live_provider"] = bool(state and state.get("data_source") == "open_meteo")
        checks["risk_data"] = self.get_risk(location_id) is not None
        try:
            models = self._session.get(f"{self.base_url}/forecast/models", timeout=5).json()
            checks["real_model"] = any(
                m.get("authenticity") == "REAL" and m.get("status") == "VALIDATED"
                for m in models.get("models", [])
            )
        except requests.RequestException:
            checks["real_model"] = False
        try:
            copilot_url = os.environ.get("COPILOT_API_URL", "http://localhost:8005")
            copilot = self._session.get(f"{copilot_url}/health/live", timeout=3).json()
            checks["copilot"] = copilot.get("status") in {"healthy", "alive", True}
        except requests.RequestException:
            checks["copilot"] = False
        try:
            rag = self._session.get(
                os.environ.get("RAG_SERVICE_URL", "http://localhost:8004") + "/health",
                timeout=5,
            ).json()
            checks["rag"] = rag.get("status") == "healthy"
        except requests.RequestException:
            checks["rag"] = False
        return {"live": all(checks.values()), "checks": checks}

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
        loc_id = str(loc["id"])
        state = self.get_current_state(loc_id)
        risk = self.get_risk(loc_id)
        if state:
            hist = self.get_historical(loc_id)
            if not hist:
                return {"district": district, "available": False, "error": "No verified history"}
            max_values = [h.get("max_temp") for h in hist if h.get("max_temp") is not None]
            min_values = [h.get("min_temp") for h in hist if h.get("min_temp") is not None]
            if not max_values or not min_values:
                return {"district": district, "available": False, "error": "No daily extrema"}
            total_rain = round(sum(h.get("rainfall", 0) or 0 for h in hist), 1)
            avg_max = round(sum(max_values) / len(max_values), 1)
            avg_min = round(sum(min_values) / len(min_values), 1)
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
                "avg_max_temp": avg_max,
                "avg_min_temp": avg_min,
                "total_rainfall_ytd": total_rain,
                "rainy_days": sum(1 for h in hist if (h.get("rainfall") or 0) > 0),
                "extreme_heat_days": sum(1 for h in hist if (h.get("max_temp") or 0) >= 35),
                "risk_level": risk_level,
            }
        return {
            "district": district,
            "available": False,
            "rainy_days": 0,
            "extreme_heat_days": 0,
            "error": "No data available",
        }

    # ------------------------------------------------------------------
    # Knowledge Base (RAG)
    # ------------------------------------------------------------------
    def search_knowledge(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search the RAG knowledge base via gateway (KnowledgeAPI-backed)."""
        try:
            resp = self._session.post(
                f"{self.base_url}/rag/ask",
                json={"query": query, "k": k},
                timeout=max(self.timeout, 120),
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return [
                {
                    "rank": int(r.get("rank", i + 1)),
                    "score": float(r.get("score", 0)),
                    "text": r.get("text", r.get("content", "")),
                    "document_id": r.get("document_id", ""),
                    "chunk_id": r.get("chunk_id", ""),
                }
                for i, r in enumerate(results)
            ]
        except Exception as e:
            # Fallback to dedicated RAG service on :8004
            rag_url = os.environ.get("RAG_SERVICE_URL", "http://localhost:8004").rstrip("/")
            try:
                resp = self._session.post(
                    f"{rag_url}/search",
                    json={"query": query, "top_k": k},
                    timeout=max(self.timeout, 120),
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                return [
                    {
                        "rank": i + 1,
                        "score": float(r.get("score", 0)),
                        "text": r.get("content", r.get("text", "")),
                        "document_id": r.get("document_id", ""),
                        "chunk_id": r.get("chunk_id", ""),
                    }
                    for i, r in enumerate(results)
                ]
            except Exception as nested:
                logger.warning("Knowledge base search unavailable: %s / %s", e, nested)
                raise RuntimeError(f"Knowledge base search unavailable: {e}") from nested

    def ingest_document(
        self,
        title: str,
        source: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ingest a document into the RAG knowledge base."""
        try:
            resp = self._session.post(
                f"{self.base_url}/rag/ingest",
                json={
                    "title": title,
                    "source": source,
                    "content": content,
                    "tags": tags or [],
                },
                timeout=max(self.timeout, 120),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "document_id": data.get("document_id", ""),
                "chunks": data.get("chunks_created", 0),
            }
        except Exception as e:
            logger.warning("Document ingestion failed: %s", e)
            raise RuntimeError(f"Document ingestion failed: {e}") from e

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------
    def get_feedback_data(self) -> list[dict[str, Any]]:
        """Return persisted feedback rows for the analytics page."""
        try:
            # Prefer dedicated list endpoint when present; fall back to synthesizing from stats.
            resp = self._session.get(f"{self.base_url}/feedback/stats", timeout=self.timeout)
            resp.raise_for_status()
            stats = resp.json()
            # Try recent entries endpoint if added; otherwise keep empty list when total is 0.
            list_resp = self._session.get(f"{self.base_url}/feedback/entries", timeout=self.timeout)
            if list_resp.status_code == 200:
                payload = list_resp.json()
                entries = payload.get("entries", payload if isinstance(payload, list) else [])
                if isinstance(entries, list):
                    return [
                        {
                            "date": e.get("date", e.get("created_at", "")),
                            "location": e.get("location", e.get("location_id", "unknown")),
                            "rating": float(e.get("rating", 0) or 0),
                            "type": e.get("type", e.get("feedback_type", "general")),
                            "comment": e.get("comment", ""),
                        }
                        for e in entries
                        if isinstance(e, dict)
                    ]
            if int(stats.get("total_feedback", 0) or 0) == 0:
                return []
            return []
        except Exception:
            logger.info("Feedback stats unavailable")
            return []

    def submit_feedback(
        self,
        location_id: str,
        rating: float,
        feedback_type: str = "general",
        comment: str = "",
    ) -> dict[str, Any]:
        """Submit general feedback through the gateway."""
        resp = self._session.post(
            f"{self.base_url}/feedback/general",
            json={
                "location_id": location_id,
                "feedback_type": feedback_type,
                "rating": rating,
                "comment": comment,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Version History & Comparison
    # ------------------------------------------------------------------
    def get_version_history(self, entity_id: str) -> list[dict[str, Any]]:
        """Get version history for a digital twin entity."""
        try:
            resp = self._session.get(
                f"{self.base_url}/twin/history/{entity_id}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            versions = payload.get("versions", []) if isinstance(payload, dict) else []
            return [
                {
                    "version_number": v.get("version_number", i + 1),
                    "created_at": v.get("created_at", ""),
                    "entity_id": entity_id,
                    "state": v.get("state", {}),
                }
                for i, v in enumerate(versions)
            ]
        except Exception as e:
            logger.warning("Version history unavailable for %s: %s", entity_id, e)
            return []

    def compare_versions(
        self, entity_id: str, version_a: int, version_b: int
    ) -> list[dict[str, Any]] | None:
        """Compare two versions of a twin entity state."""
        history = self.get_version_history(entity_id)
        if not history:
            return None

        state_a: dict[str, Any] | None = None
        state_b: dict[str, Any] | None = None
        for v in history:
            if v.get("version_number") == version_a:
                state_a = v.get("state", {})
            if v.get("version_number") == version_b:
                state_b = v.get("state", {})

        if state_a is None or state_b is None:
            return None

        compare_keys = [
            "temperature_2m",
            "precipitation_mm",
            "humidity_pct",
            "pressure_hpa",
            "wind_speed_10m",
        ]
        rows: list[dict[str, Any]] = []
        for key in compare_keys:
            val_a = state_a.get(key, 0)
            val_b = state_b.get(key, 0)
            try:
                delta = float(val_b) - float(val_a)
            except (TypeError, ValueError):
                delta = 0
            rows.append(
                {
                    "Variable": key,
                    "Version A": val_a,
                    "Version B": val_b,
                    "Delta": round(delta, 3),
                }
            )
        return rows

    def list_disaster_events(self) -> list[dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/disaster/events", timeout=self.timeout)
            if resp.ok:
                return list(resp.json().get("items") or [])
        except requests.RequestException as exc:
            logger.warning("Disaster events unavailable: %s", exc)
        return []

    def list_disaster_jobs(self, event_id: str | None = None) -> list[dict[str, Any]]:
        try:
            params = {"event_id": event_id} if event_id else None
            resp = requests.get(
                f"{self.base_url}/disaster/jobs", params=params, timeout=self.timeout
            )
            if resp.ok:
                return list(resp.json().get("items") or [])
        except requests.RequestException as exc:
            logger.warning("Disaster jobs unavailable: %s", exc)
        return []

    def get_disaster_job(self, job_id: str) -> dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/disaster/jobs/{job_id}", timeout=self.timeout)
            if resp.ok:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("Disaster job unavailable: %s", exc)
        return {"available": False}

    def get_disaster_assessment(self, assessment_id: str) -> dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}/disaster/assessments/{assessment_id}", timeout=self.timeout
            )
            if resp.ok:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("Disaster assessment unavailable: %s", exc)
        return {"available": False}

    def get_disaster_geojson(self, assessment_id: str, layer: str = "buildings") -> dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}/disaster/assessments/{assessment_id}/geojson",
                params={"layer": layer, "limit": 2000},
                timeout=self.timeout,
            )
            if resp.ok:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("Disaster geojson unavailable: %s", exc)
        return {"type": "FeatureCollection", "features": []}

    def list_disaster_models(self) -> dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/disaster/models", timeout=self.timeout)
            if resp.ok:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("Disaster models unavailable: %s", exc)
        return {"items": [], "available": False}

    def get_twin_overlay(self, location_id: str) -> dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}/disaster/twin/{location_id}", timeout=self.timeout
            )
            if resp.ok:
                return resp.json()
        except requests.RequestException as exc:
            logger.warning("Twin overlay unavailable: %s", exc)
        return {"available": False, "location_id": location_id}

    def create_disaster_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(f"{self.base_url}/disaster/events", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def upload_disaster_scene(
        self, event_id: str, file_bytes: bytes, filename: str, license_name: str
    ) -> dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/disaster/ingest/upload",
            files={"file": (filename, file_bytes, "image/tiff")},
            data={"event_id": event_id, "license": license_name},
            timeout=max(self.timeout, 60),
        )
        resp.raise_for_status()
        return resp.json()

    def create_disaster_job(self, event_id: str, twin_sync: bool = True) -> dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/disaster/jobs",
            json={"event_id": event_id, "twin_sync": twin_sync},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_disaster_report(
        self, assessment_id: str, location: str, fmt: str = "markdown"
    ) -> bytes:
        try:
            resp = requests.get(
                f"{self.base_url}/disaster/assessments/{assessment_id}/report",
                params={"location": location, "fmt": fmt},
                timeout=self.timeout,
            )
            if resp.ok:
                return resp.content
        except requests.RequestException as exc:
            logger.warning("Disaster report unavailable: %s", exc)
        return b"No verified disaster assessment is available.\n"


def create_api_client() -> DashboardAPI:
    from dashboard.config.config import API_BASE_URL, API_TIMEOUT

    return DashboardAPI(base_url=API_BASE_URL, timeout=API_TIMEOUT)
