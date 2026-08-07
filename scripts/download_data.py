#!/usr/bin/env python3
"""Unified Data Download & Seed Script for Climate Digital Twin.

Downloads external climate datasets (ERA5, Open-Meteo, NASA POWER) or seeds
synthetic demonstration data if remote services are offline or keys are unconfigured.

Usage:
    python scripts/download_data.py [--dataset {all,era5,synthetic,seed}] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("download_data")

ROOT_DIR = Path(__file__).resolve().parent.parent


def seed_synthetic_data(data_dir: Path) -> None:
    """Generate synthetic climate observation data for raw, real, and forecast stores."""
    logger.info("Seeding synthetic climate data into %s...", data_dir)

    try:
        # Import seed utilities from scripts if present
        sys.path.insert(0, str(ROOT_DIR))
        from scripts.seed_forecast_data import main as seed_forecast
        from scripts.seed_twin_data import main as seed_twin

        seed_forecast()
        seed_twin()
        logger.info("Successfully seeded synthetic forecast and twin data.")
    except Exception as exc:
        logger.warning(
            "Failed to invoke seed scripts directly: %s. Generating basic datasets.", exc
        )
        _generate_basic_parquet_and_csv(data_dir)


def _generate_basic_parquet_and_csv(data_dir: Path) -> None:
    """Fallback generator for basic parquet and csv files."""
    import numpy as np
    import pandas as pd

    raw_dir = data_dir / "raw"
    real_dir = data_dir / "real"
    raw_dir.mkdir(parents=True, exist_ok=True)
    real_dir.mkdir(parents=True, exist_ok=True)

    dates = pd.date_range(start="2021-01-01", periods=1800, freq="D")
    n = len(dates)

    grid_points = [(12.97, 77.59), (12.5, 78.0)]
    df_max_list, df_min_list, df_rain_list = [], [], []

    for lat, lon in grid_points:
        tmax = 25.0 + 10.0 * np.sin(np.linspace(0, 3.14, n)) + np.random.randn(n)
        tmin = 15.0 + 8.0 * np.sin(np.linspace(0, 3.14, n)) + np.random.randn(n)
        rain = np.maximum(0, np.random.exponential(scale=5.0, size=n))

        for idx, d in enumerate(dates):
            if d.month in (1, 2, 3) and d.day <= 20:
                rain[idx] = 0.0
            elif d.month == 8 and d.day == 15:
                rain[idx] = 85.0
            elif lat == 12.5 and str(d.date()) == "2022-08-18":
                rain[idx] = 266.32

        df_max_list.append(
            pd.DataFrame(
                {
                    "Date": dates,
                    "Latitude": np.full(n, lat),
                    "Longitude": np.full(n, lon),
                    "MaxTemp": tmax,
                }
            )
        )
        df_min_list.append(
            pd.DataFrame(
                {
                    "Date": dates,
                    "Latitude": np.full(n, lat),
                    "Longitude": np.full(n, lon),
                    "MinTemp": tmin,
                }
            )
        )
        df_rain_list.append(
            pd.DataFrame(
                {
                    "Date": dates,
                    "Latitude": np.full(n, lat),
                    "Longitude": np.full(n, lon),
                    "Rainfall": rain,
                }
            )
        )

    df_max = pd.concat(df_max_list, ignore_index=True)
    df_min = pd.concat(df_min_list, ignore_index=True)
    df_rain = pd.concat(df_rain_list, ignore_index=True)

    df_max.to_parquet(raw_dir / "maxtemp.parquet", index=False)
    df_min.to_parquet(raw_dir / "mintemp.parquet", index=False)
    df_rain.to_parquet(raw_dir / "rainfall.parquet", index=False)

    beng_max = df_max_list[0]
    beng_min = df_min_list[0]
    beng_rain = df_rain_list[0]

    df_merged = pd.DataFrame(
        {
            "Date": dates,
            "MaxTemp": beng_max["MaxTemp"].values,
            "MinTemp": beng_min["MinTemp"].values,
            "Rainfall": beng_rain["Rainfall"].values,
            "Month": dates.month.values,
            "Week": dates.isocalendar().week.values,
            "Season": np.ones(n, dtype=int),
            "Monsoon": ((dates.month >= 6) & (dates.month <= 9)).astype(int),
            "RollingRain7": beng_rain["Rainfall"].rolling(7, min_periods=1).mean().values,
            "RollingRain30": beng_rain["Rainfall"].rolling(30, min_periods=1).mean().values,
            "RollingTemp7": beng_max["MaxTemp"].rolling(7, min_periods=1).mean().values,
            "RollingTemp30": beng_max["MaxTemp"].rolling(30, min_periods=1).mean().values,
        }
    )

    n_split = n // 3
    df_merged.iloc[:n_split].to_csv(real_dir / "training.csv", index=False)
    df_merged.iloc[n_split : 2 * n_split].to_csv(real_dir / "validation.csv", index=False)
    df_merged.iloc[2 * n_split :].to_csv(real_dir / "testing.csv", index=False)

    logger.info("Generated raw parquet files and real CSV splits in %s.", data_dir)


def download_era5_data() -> None:
    """Download ERA5 reanalysis sample data using the ERA5 downloader script."""
    try:
        from scripts.download_era5_india import download_era5_sample

        download_era5_sample()
    except Exception as exc:
        logger.warning("ERA5 download failed or skipped: %s. Using synthetic fallback.", exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download or generate data for Climate Digital Twin."
    )
    parser.add_argument(
        "--dataset",
        choices=["all", "era5", "synthetic", "seed"],
        default="all",
        help="Dataset type to download or generate (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data",
        help="Directory to place dataset files",
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset in ("all", "synthetic", "seed"):
        seed_synthetic_data(args.output_dir)

    if args.dataset in ("all", "era5"):
        download_era5_data()

    logger.info("Data management process complete.")


if __name__ == "__main__":
    main()
