"""ERA5 India Bulk Download Pipeline.

Downloads ERA5 hourly data for India subcontinent from ECMWF CDS.
Supports resume, retry, checkpointing, and manifest tracking.

Usage: python scripts/download_era5_india.py [--year 2021] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# India bounding box
INDIA_BBOX = {"north": 38.0, "south": 6.0, "west": 68.0, "east": 98.0}
KARNATAKA_BBOX = {"north": 18.5, "south": 11.0, "west": 74.0, "east": 79.0}

ERA5_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "surface_pressure",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
]

OUTPUT_DIR = Path("data/validation/era5/india")
# Will be overridden per region


def get_output_dir(region: str) -> Path:
    return Path(f"data/validation/era5/{region}")


MANIFEST_PATH = OUTPUT_DIR / "download_manifest.json"


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded_months": {}, "failed_months": {}, "started_at": None}


def save_manifest(manifest: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)


def download_month(
    year: int,
    month: int,
    bbox: dict[str, float],
    variables: list[str] | None = None,
    dry_run: bool = False,
) -> Path | None:
    """Download one month of ERA5 hourly data using CDS API."""
    import cdsapi

    key = f"{year}-{month:02d}"
    output_path = OUTPUT_DIR / "raw" / f"era5_{year}{month:02d}.nc"

    manifest = load_manifest()
    if key in manifest["downloaded_months"] and output_path.exists():
        logger.info("Already downloaded: %s", key)
        return output_path

    if dry_run:
        logger.info("[DRY RUN] Would download: %s", key)
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "raw").mkdir(exist_ok=True)

    variables = variables or ERA5_VARIABLES
    client = cdsapi.Client()

    try:
        logger.info("Downloading %s (India, %d vars)...", key, len(variables))
        t0 = time.time()
        client.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": variables,
                "year": str(year),
                "month": f"{month:02d}",
                "day": [f"{d:02d}" for d in range(1, 32)],
                "time": ["00:00", "06:00", "12:00", "18:00"],
                "area": [bbox["north"], bbox["west"], bbox["south"], bbox["east"]],
            },
            str(output_path),
        )
        elapsed = time.time() - t0
        size_mb = output_path.stat().st_size / 1024 / 1024 if output_path.exists() else 0

        manifest["downloaded_months"][key] = {
            "path": str(output_path),
            "size_mb": round(size_mb, 2),
            "elapsed_s": round(elapsed, 1),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        save_manifest(manifest)
        logger.info("Downloaded: %s (%.1f MB, %.0fs)", key, size_mb, elapsed)
        return output_path

    except Exception as e:
        manifest["failed_months"][key] = str(e)
        save_manifest(manifest)
        logger.warning("Failed: %s — %s", key, e)
        return None


def download_year_range(
    start_year: int,
    end_year: int,
    bbox: dict[str, float],
    dry_run: bool = False,
) -> dict:
    """Download all months in a year range with resume support."""
    manifest = load_manifest()
    if not manifest["started_at"]:
        manifest["started_at"] = datetime.now(timezone.utc).isoformat()
        manifest["bbox"] = bbox
        save_manifest(manifest)

    results = {"downloaded": 0, "failed": 0, "skipped": 0}
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            key = f"{year}-{month:02d}"
            if key in manifest["downloaded_months"]:
                results["skipped"] += 1
                continue
            result = download_month(year, month, bbox, dry_run=dry_run)
            if result:
                results["downloaded"] += 1
            else:
                results["failed"] += 1

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="ERA5 India Bulk Download")
    parser.add_argument("--start-year", type=int, default=2021)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--region", choices=["karnataka", "india"], default="karnataka")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bbox = KARNATAKA_BBOX if args.region == "karnataka" else INDIA_BBOX
    logger.info("Region: %s, %d-%d, bbox=%s", args.region, args.start_year, args.end_year, bbox)

    results = download_year_range(args.start_year, args.end_year, bbox, dry_run=args.dry_run)
    logger.info(
        "Complete: %d downloaded, %d failed, %d skipped",
        results["downloaded"],
        results["failed"],
        results["skipped"],
    )


if __name__ == "__main__":
    main()
