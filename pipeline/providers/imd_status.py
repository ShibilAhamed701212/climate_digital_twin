from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pipeline.providers.fetch_result import AUTH_REQUIRED, FetchResult
from simulator.models.weather import DataSource

_logger = logging.getLogger(__name__)

IMD_ACTIVATION_DOCS = """
IMD (India Meteorological Department) data requires:
  1. Registration at https://dsp.imd.gov.in/
  2. API credentials (client_id, client_secret)
  3. IMD data access agreement
  4. Set IMD_CLIENT_ID and IMD_CLIENT_SECRET in .env

Once configured:
  - IMD_DAILY_RAINFALL: 0.25° grid, 1901-present, India landmass
  - IMD_DAILY_TEMPERATURE: 1.0° grid, 1951-present, India landmass

Until credentials are available, IMD returns AUTH_REQUIRED.
"""


def fetch_imd(
    lat: float,
    lon: float,
    _location_id: str = "auto",
    **_kwargs: Any,
) -> FetchResult:
    now = datetime.now(UTC)
    _logger.info("IMD fetch attempted but auth not configured (lat=%.4f, lon=%.4f)", lat, lon)
    return FetchResult(
        provider=DataSource.IMD,
        status="FAILED",
        observations=[],
        error_code=AUTH_REQUIRED,
        error_message=IMD_ACTIVATION_DOCS.strip(),
        requested_at=now,
        completed_at=now,
        request_metadata={
            "latitude": lat,
            "longitude": lon,
            "note": "IMD requires registration at https://dsp.imd.gov.in/",
        },
    )
