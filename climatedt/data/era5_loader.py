"""Phase 12.5 — ERA5 integration layer.

Downloads atmospheric reanalysis from ECMWF Climate Data Store.
Requires CDS API credentials to be set as environment variables:
  CDS_API_URL = https://cds.climate.copernicus.eu/
  CDS_API_KEY = {uid}:{api_key}

On first use, register at https://cds.climate.copernicus.eu/.
The API key is free and grants access to ERA5 hourly data.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ERA5_DIR = Path("data/validation/era5")

ERA5_VARIABLES = {
    "temperature_2m": {"short_name": "2t", "unit": "K", "level": "single"},
    "dewpoint_2m": {"short_name": "2d", "unit": "K", "level": "single"},
    "relative_humidity": {"derived": True, "unit": "%", "compute": "100 * (es(Td) / es(T))"},
    "u_component_wind_10m": {"short_name": "10u", "unit": "m/s", "level": "single"},
    "v_component_wind_10m": {"short_name": "10v", "unit": "m/s", "level": "single"},
    "wind_speed_10m": {"derived": True, "unit": "m/s", "compute": "sqrt(u^2 + v^2)"},
    "surface_pressure": {"short_name": "sp", "unit": "Pa", "level": "single"},
    "surface_solar_radiation_downwards": {"short_name": "ssrd", "unit": "J/m2", "level": "single"},
    "surface_thermal_radiation_downwards": {
        "short_name": "strd",
        "unit": "J/m2",
        "level": "single",
    },
    "total_precipitation": {"short_name": "tp", "unit": "m", "level": "single"},
}

BENGALURU_COORDS = {
    "north": 13.5,
    "south": 12.5,
    "west": 77.0,
    "east": 78.0,
}


def get_cds_credentials() -> tuple[str, str] | None:
    """Get CDS API credentials from environment or .cdsapirc file."""
    url = os.environ.get("CDS_API_URL", "https://cds.climate.copernicus.eu/api")
    key = os.environ.get("CDS_API_KEY", "")

    if not key:
        cds_rc = Path.home() / ".cdsapirc"
        if cds_rc.exists():
            with open(cds_rc, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("key"):
                        key = line.split(":", 1)[1].strip()
                    elif line.startswith("url"):
                        url = line.split(":", 1)[1].strip().rstrip("/")
    if not key:
        return None
    return url, key


def download_era5(
    year: int,
    month: int,
    variables: list[str] | None = None,
    region: dict[str, float] | None = None,
    output_dir: str | Path = DEFAULT_ERA5_DIR,
    format: str = "netcdf",
) -> Path | None:
    """Download ERA5 hourly data for one month using CDS API.

    Requires CDS_API_URL and CDS_API_KEY environment variables.

    Returns path to downloaded file, or None if credentials unavailable.
    """
    creds = get_cds_credentials()
    if creds is None:
        logger.warning(
            "CDS API credentials not found. Set CDS_API_URL and CDS_API_KEY "
            "environment variables, or create ~/.cdsapirc."
        )
        return None

    try:
        import cdsapi
    except ImportError:
        logger.warning("cdsapi not installed — run: pip install cdsapi")
        return None

    region = region or BENGALURU_COORDS
    var_list = variables or [
        "2m_temperature",
        "2m_dewpoint_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "surface_pressure",
        "surface_solar_radiation_downwards",
        "surface_thermal_radiation_downwards",
        "total_precipitation",
    ]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"era5_{year}{month:02d}.nc"
    output_path = out_dir / filename

    if output_path.exists():
        logger.info("ERA5 file already exists: %s", output_path)
        return output_path

    client = cdsapi.Client(url=creds[0], key=creds[1])

    request = {
        "product_type": "reanalysis",
        "format": format,
        "variable": var_list,
        "year": str(year),
        "month": f"{month:02d}",
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(0, 24)],
        "area": [region["north"], region["west"], region["south"], region["east"]],
    }

    logger.info("Downloading ERA5 for %d-%02d...", year, month)
    client.retrieve(
        "reanalysis-era5-single-levels",
        request,
        str(output_path),
    )
    logger.info("ERA5 saved to %s", output_path)
    return output_path
