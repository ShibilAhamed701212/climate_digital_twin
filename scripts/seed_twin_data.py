#!/usr/bin/env python3
"""Seed the Twin State Manager with realistic initial data for Karnataka districts.

Usage:
    python scripts/seed_twin_data.py [--engine-url URL]

If ENGINE_URL or --engine-url is provided, uses the REST API (when the
service is already running).  Otherwise imports the engine directly
for offline seeding into a fresh DigitalTwinEngine instance.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Karnataka District Data ──────────────────────────────────────────
# Realistic climate averages for June (monsoon season) in Karnataka

DISTRICTS: list[dict[str, Any]] = [
    {
        "id": "KA-BLR-001",
        "name": "Bengaluru Urban",
        "lat": 12.97,
        "lon": 77.59,
        "rainfall": 110,
        "max_temp": 29,
        "min_temp": 21,
    },
    {
        "id": "KA-MYS-001",
        "name": "Mysuru",
        "lat": 12.29,
        "lon": 76.63,
        "rainfall": 80,
        "max_temp": 28,
        "min_temp": 20,
    },
    {
        "id": "KA-BEL-001",
        "name": "Belagavi",
        "lat": 15.85,
        "lon": 74.50,
        "rainfall": 240,
        "max_temp": 27,
        "min_temp": 21,
    },
    {
        "id": "KA-MNG-001",
        "name": "Dakshina Kannada",
        "lat": 12.91,
        "lon": 74.85,
        "rainfall": 350,
        "max_temp": 28,
        "min_temp": 23,
    },
    {
        "id": "KA-HBL-001",
        "name": "Dharwad",
        "lat": 15.36,
        "lon": 75.13,
        "rainfall": 180,
        "max_temp": 28,
        "min_temp": 21,
    },
    {
        "id": "KA-GUL-001",
        "name": "Kalaburagi",
        "lat": 17.33,
        "lon": 76.83,
        "rainfall": 120,
        "max_temp": 34,
        "min_temp": 24,
    },
    {
        "id": "KA-SHM-001",
        "name": "Shivamogga",
        "lat": 13.93,
        "lon": 75.57,
        "rainfall": 200,
        "max_temp": 27,
        "min_temp": 21,
    },
    {
        "id": "KA-UDP-001",
        "name": "Udupi",
        "lat": 13.34,
        "lon": 74.75,
        "rainfall": 380,
        "max_temp": 29,
        "min_temp": 24,
    },
]


def seed_via_api(engine_url: str) -> None:
    """Seed the twin state manager via its REST API."""
    import random

    import requests

    today = datetime.now()
    for dist in DISTRICTS:
        # Ingest 7 days of historical observations (simulating real data)
        for day_offset in range(7, 0, -1):
            date = today - timedelta(days=day_offset)
            jitter = lambda mu, sigma: max(0, round(random.gauss(mu, sigma), 1))  # noqa: E731
            payload = {
                "location_id": dist["id"],
                "latitude": dist["lat"],
                "longitude": dist["lon"],
                "district": dist["name"],
                "timestamp": date.isoformat(),
                "rainfall": jitter(dist["rainfall"], 25),
                "max_temp": round(random.gauss(dist["max_temp"], 1.5), 1),
                "min_temp": round(random.gauss(dist["min_temp"], 1.0), 1),
                "risk_score": round(random.uniform(10, 50), 1),
                "prediction_confidence": 0.85,
                "data_source": "IMD",
            }
            resp = requests.post(f"{engine_url}/state/sync", json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(
                "Seeded %s day -%d (v%s)", dist["id"], day_offset, resp.json()["version_id"]
            )

        # Verify
        resp = requests.get(
            f"{engine_url}/state/current", params={"location_id": dist["id"]}, timeout=10
        )
        if resp.status_code == 200:
            logger.info(
                "✅ %s (%s) current state: %.1f°C, %.1fmm rain",
                dist["id"],
                dist["name"],
                resp.json()["max_temp"],
                resp.json()["rainfall"],
            )
        else:
            logger.warning("⚠️  %s state check: HTTP %d", dist["id"], resp.status_code)


def seed_direct() -> None:
    """Seed by importing the engine directly (for offline/boot-time use)."""
    import random

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from simulator.engine.twin_engine import DigitalTwinEngine
    from simulator.entities.climate_entity import ClimateEntity

    engine = DigitalTwinEngine()
    today = datetime.now()

    for dist in DISTRICTS:
        # Ingest 7 days of historical data
        for day_offset in range(7, 0, -1):
            date = today - timedelta(days=day_offset)
            jitter = lambda mu, sigma: max(0, round(random.gauss(mu, sigma), 1))  # noqa: E731
            entity = ClimateEntity(
                location_id=dist["id"],
                latitude=dist["lat"],
                longitude=dist["lon"],
                district=dist["name"],
                timestamp=date.isoformat(),
                rainfall=jitter(dist["rainfall"], 25),
                max_temp=round(random.gauss(dist["max_temp"], 1.5), 1),
                min_temp=round(random.gauss(dist["min_temp"], 1.0), 1),
                risk_score=round(random.uniform(10, 50), 1),
                prediction_confidence=0.85,
                data_source="IMD",
            )
            result = engine.ingest_observation(entity)
            logger.info("Seeded %s day -%d (v%s)", dist["id"], day_offset, result["version_id"])

        # Verify
        state = engine.get_current_state(dist["id"])
        if state:
            logger.info(
                "✅ %s (%s) current state: %.1f°C, %.1fmm rain",
                dist["id"],
                dist["name"],
                state["max_temp"],
                state["rainfall"],
            )

    # Print summary
    ids = engine.service.state_manager.get_all_location_ids()
    logger.info("Total locations in twin: %d — %s", len(ids), ", ".join(sorted(ids)))


def main() -> None:
    engine_url = os.environ.get("ENGINE_URL") or (
        sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else None
    )
    if engine_url:
        seed_via_api(engine_url)
    else:
        seed_direct()


if __name__ == "__main__":
    main()
