"""Seed configured dashboard locations from the live Open-Meteo API."""

import requests

from dashboard.config.config import SAMPLE_LOCATIONS

for location in SAMPLE_LOCATIONS:
    current = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": location["lat"],
            "longitude": location["lon"],
            "current": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,rain,precipitation",
            "timezone": "UTC",
        },
        timeout=30,
    ).json()["current"]
    try:
        old = requests.get(f"http://localhost:8000/twin/state/{location['id']}", timeout=10).json()
    except requests.RequestException:
        old = {
            "temperature_2m": 0,
            "precipitation_mm": 0,
            "humidity_pct": 0,
            "pressure_hpa": 0,
            "wind_speed_10m": 0,
        }
    payload = {
        "entity_id": location["id"],
        "delta_temperature": current["temperature_2m"] - old.get("temperature_2m", 0),
        "delta_precipitation": current.get("precipitation", current.get("rain", 0))
        - old.get("precipitation_mm", 0),
        "delta_humidity": current["relative_humidity_2m"] - old.get("humidity_pct", 0),
        "delta_pressure": current["pressure_msl"] - old.get("pressure_hpa", 0),
        "delta_wind_speed": current["wind_speed_10m"] - old.get("wind_speed_10m", 0),
        "source": "open_meteo",
    }
    response = requests.post("http://localhost:8000/twin/state", json=payload, timeout=20)
    sync = requests.post(
        "http://localhost:8001/state/sync",
        json={
            "location_id": location["id"],
            "latitude": location["lat"],
            "longitude": location["lon"],
            "district": location["district"],
            "timestamp": current["time"],
            "rainfall": current.get("precipitation", current.get("rain", 0)),
            "max_temp": current["temperature_2m"],
            "min_temp": current["temperature_2m"],
            "data_source": "open_meteo",
        },
        timeout=20,
    )
    print(location["id"], response.status_code, sync.status_code, current["temperature_2m"])
