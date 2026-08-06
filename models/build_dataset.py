"""Fetch real historical climate data and build chronologically-split dataset.

Usage:
    python -m models.build_dataset [--location LAT,LON,NAME] [--years 5]

Produces data/real/{training,validation,testing}.csv + dataset_manifest.json
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SEASON_MAP: dict[int, str] = {
    1: "Winter",
    2: "Winter",
    3: "Summer",
    4: "Summer",
    5: "Summer",
    6: "Monsoon",
    7: "Monsoon",
    8: "Monsoon",
    9: "Monsoon",
    10: "Post-Monsoon",
    11: "Post-Monsoon",
    12: "Winter",
}
MONSOON_MONTHS = [6, 7, 8, 9]


def fetch_open_meteo(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=auto"
    )
    logger.info("Fetching data from Open-Meteo: %s", url)
    resp = urllib.request.urlopen(url, timeout=60)
    data = json.loads(resp.read().decode())
    daily = data.get("daily", {})
    df = pd.DataFrame(
        {
            "Date": daily.get("time", []),
            "MaxTemp": daily.get("temperature_2m_max", []),
            "MinTemp": daily.get("temperature_2m_min", []),
            "Rainfall": daily.get("precipitation_sum", []),
        }
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df["Rainfall"] = df["Rainfall"].fillna(0.0)
    df[["MaxTemp", "MinTemp"]] = df[["MaxTemp", "MinTemp"]].ffill()
    logger.info("Fetched %d daily records", len(df))
    return df


def engineer_features(df: pd.DataFrame, lat: float, lon: float, name: str) -> pd.DataFrame:
    df = df.sort_values("Date").reset_index(drop=True)
    df["Latitude"] = lat
    df["Longitude"] = lon
    df["LocationName"] = name
    dates = pd.to_datetime(df["Date"])
    df["Month"] = dates.dt.month
    df["Week"] = dates.dt.isocalendar().week.astype(int)
    df["Season"] = df["Month"].map(SEASON_MAP)
    df["Monsoon"] = df["Month"].isin(MONSOON_MONTHS).astype(int)
    df["RollingRain7"] = df["Rainfall"].rolling(7, min_periods=1).mean()
    df["RollingRain30"] = df["Rainfall"].rolling(30, min_periods=1).mean()
    df["RollingTemp7"] = df["MaxTemp"].rolling(7, min_periods=1).mean()
    df["RollingTemp30"] = df["MaxTemp"].rolling(30, min_periods=1).mean()
    float_cols = df.select_dtypes(include=[np.number]).columns
    skip = {"Month", "Week", "Monsoon", "Latitude", "Longitude"}
    for col in float_cols:
        if col not in skip:
            df[col] = df[col].round(2)
    return df


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build_dataset(
    lat: float = 12.97,
    lon: float = 77.59,
    name: str = "Bengaluru",
    years: int = 5,
    output_dir: str = "data/real",
) -> dict[str, Any]:
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=years * 365 + 1)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    raw = fetch_open_meteo(lat, lon, start_str, end_str)
    df = engineer_features(raw, lat, lon, name)
    n = len(df)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    train_df = df.iloc[:train_end].reset_index(drop=True)
    val_df = df.iloc[train_end:val_end].reset_index(drop=True)
    test_df = df.iloc[val_end:].reset_index(drop=True)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_path = out / "training.csv"
    val_path = out / "validation.csv"
    test_path = out / "testing.csv"

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    manifest = {
        "source": "open-meteo-archive",
        "source_url": (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start_str}&end_date={end_str}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        ),
        "location": {"name": name, "latitude": lat, "longitude": lon},
        "date_range": {"start": start_str, "end": end_str},
        "total_records": n,
        "splits": {
            "training": {
                "records": len(train_df),
                "date_range": {
                    "start": str(train_df["Date"].iloc[0].date()),
                    "end": str(train_df["Date"].iloc[-1].date()),
                },
            },
            "validation": {
                "records": len(val_df),
                "date_range": {
                    "start": str(val_df["Date"].iloc[0].date()),
                    "end": str(val_df["Date"].iloc[-1].date()),
                },
            },
            "testing": {
                "records": len(test_df),
                "date_range": {
                    "start": str(test_df["Date"].iloc[0].date()),
                    "end": str(test_df["Date"].iloc[-1].date()),
                },
            },
        },
        "columns": list(df.columns),
        "feature_columns": [
            "Rainfall",
            "MaxTemp",
            "MinTemp",
            "Month",
            "Week",
            "Season",
            "Monsoon",
            "RollingRain7",
            "RollingRain30",
            "RollingTemp7",
            "RollingTemp30",
        ],
        "target_columns": ["Rainfall", "MaxTemp", "MinTemp"],
        "checksums": {
            "training.csv": _checksum(train_path),
            "validation.csv": _checksum(val_path),
            "testing.csv": _checksum(test_path),
        },
        "built_at": datetime.now(UTC).isoformat(),
    }
    manifest_path = out / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(
        "Dataset built at %s: %d records, %d train / %d val / %d test",
        output_dir,
        n,
        len(train_df),
        len(val_df),
        len(test_df),
    )
    return manifest


def verify_dataset(data_dir: str = "data/real") -> bool:
    manifest_path = Path(data_dir) / "dataset_manifest.json"
    if not manifest_path.exists():
        logger.error("No manifest found at %s", manifest_path)
        return False
    manifest = json.loads(manifest_path.read_text())
    for fname, expected_cs in manifest.get("checksums", {}).items():
        actual_cs = _checksum(Path(data_dir) / fname)
        if actual_cs != expected_cs:
            logger.error(
                "Checksum mismatch for %s: expected %s, got %s", fname, expected_cs, actual_cs
            )
            return False
    logger.info("Dataset verified: all checksums match")
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    parser = argparse.ArgumentParser(description="Build real climate dataset from Open-Meteo")
    parser.add_argument("--lat", type=float, default=12.97)
    parser.add_argument("--lon", type=float, default=77.59)
    parser.add_argument("--name", type=str, default="Bengaluru")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--output", type=str, default="data/real")
    args = parser.parse_args()
    build_dataset(args.lat, args.lon, args.name, args.years, args.output)
    verify_dataset(args.output)


if __name__ == "__main__":
    sys.exit(main())
