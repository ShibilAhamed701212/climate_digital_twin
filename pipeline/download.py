"""Module 1: Dataset Downloader.

Downloads climate datasets from configured sources (NASA POWER API)
with synthetic data fallback when offline.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

RAINFALL_RESOLUTION_DEG = 0.25
TEMP_RESOLUTION_DEG = 1.0


class DataDownloader:
    """Downloads and verifies climate datasets from remote sources."""

    def __init__(self, config_path: str = "config/data_config.yaml") -> None:
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.raw_dir = Path(self.config["data"]["raw_dir"])
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = datetime.strptime(
            self.config["date_range"]["start"], "%Y-%m-%d"
        )
        self.end_date = datetime.strptime(
            self.config["date_range"]["end"], "%Y-%m-%d"
        )

    def _generate_grid(
        self, resolution: float, bounds: dict[str, float]
    ) -> pd.DataFrame:
        """Generate a regular lat/lon grid within Karnataka bounds."""
        lats = np.arange(
            bounds["min_lat"], bounds["max_lat"] + resolution, resolution
        )
        lons = np.arange(
            bounds["min_lon"], bounds["max_lon"] + resolution, resolution
        )
        grid = []
        for lat in lats:
            for lon in lons:
                grid.append({"Latitude": round(lat, 4), "Longitude": round(lon, 4)})
        return pd.DataFrame(grid)

    def _generate_synthetic_rainfall(
        self, start_date: datetime, end_date: datetime, grid: pd.DataFrame
    ) -> pd.DataFrame:
        """Generate realistic synthetic rainfall data for fallback."""
        dates = pd.date_range(start_date, end_date, freq="D")
        records = []
        rng = np.random.default_rng(42)
        date_range_days = (end_date - start_date).days
        monsoon_phase = np.sin(
            2 * np.pi * np.arange(date_range_days + 1) / 365.0 - 0.5
        )
        monsoon_mask = monsoon_phase > 0.3
        for _, point in grid.iterrows():
            base_rainfall = 2.0 + 8.0 * monsoon_mask
            noise = rng.exponential(3.0, len(dates))
            rainfall = np.maximum(0, base_rainfall + noise)
            for i, date in enumerate(dates):
                records.append({
                    "Date": date,
                    "Latitude": point["Latitude"],
                    "Longitude": point["Longitude"],
                    "Rainfall": round(rainfall[i], 2),
                })
        return pd.DataFrame(records)

    def _generate_synthetic_temperature(
        self,
        start_date: datetime,
        end_date: datetime,
        grid: pd.DataFrame,
        is_max: bool,
    ) -> pd.DataFrame:
        """Generate realistic synthetic temperature data for fallback."""
        dates = pd.date_range(start_date, end_date, freq="D")
        records = []
        rng = np.random.default_rng(42)
        date_range_days = (end_date - start_date).days
        base_temp = 32.0 if is_max else 20.0
        amp = 5.0 if is_max else 4.0
        noise_std = 2.0 if is_max else 1.5
        for _, point in grid.iterrows():
            lat_factor = 1.0 - (point["Latitude"] - 11.5) / 7.0
            daily = base_temp + lat_factor * 3.0
            seasonal = amp * np.sin(
                2 * np.pi * np.arange(date_range_days + 1) / 365.0 - 0.5
            )
            noise = rng.normal(0, noise_std, len(dates))
            temp = daily + seasonal + noise
            for i, date in enumerate(dates):
                records.append({
                    "Date": date,
                    "Latitude": point["Latitude"],
                    "Longitude": point["Longitude"],
                    "MaxTemp" if is_max else "MinTemp": round(temp[i], 2),
                })
        return pd.DataFrame(records)

    def _try_download(self, url: str, filepath: Path) -> bool:
        """Attempt to download a file with resume support."""
        try:
            headers = {}
            if filepath.exists():
                existing_size = filepath.stat().st_size
                headers["Range"] = f"bytes={existing_size}-"
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            if response.status_code in (200, 206):
                mode = "ab" if response.status_code == 206 else "wb"
                with open(filepath, mode) as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info("Downloaded %s (%d bytes)", filepath.name, filepath.stat().st_size)
                return True
            logger.warning("HTTP %d for %s", response.status_code, url)
            return False
        except requests.RequestException as e:
            logger.warning("Download request failed for %s: %s", url, e)
            return False

    def _is_html_file(self, filepath: Path) -> bool:
        """Check if a downloaded file is actually HTML (not expected data format)."""
        try:
            with open(filepath, "rb") as f:
                head = f.read(512).lower()
            return head.startswith(b"<!doctype") or head.startswith(b"<html")
        except OSError:
            return False

    def _save_synthetic_rainfall(self, filename: str) -> Path:
        """Generate and save synthetic rainfall data."""
        logger.info("Generating synthetic rainfall data")
        bounds = self.config["karnataka_bounds"]
        grid = self._generate_grid(RAINFALL_RESOLUTION_DEG, bounds)
        df = self._generate_synthetic_rainfall(self.start_date, self.end_date, grid)
        filepath = self.raw_dir / filename
        df.to_parquet(filepath.with_suffix(".parquet"))
        logger.info(
            "Synthetic rainfall saved: %s (%d records)",
            filepath.with_suffix(".parquet").name,
            len(df),
        )
        return filepath.with_suffix(".parquet")

    def _save_synthetic_temperature(
        self, filename: str, is_max: bool
    ) -> Path:
        """Generate and save synthetic temperature data."""
        logger.info("Generating synthetic %s temperature data", "max" if is_max else "min")
        bounds = self.config["karnataka_bounds"]
        grid = self._generate_grid(TEMP_RESOLUTION_DEG, bounds)
        df = self._generate_synthetic_temperature(
            self.start_date, self.end_date, grid, is_max
        )
        filepath = self.raw_dir / filename
        df.to_parquet(filepath.with_suffix(".parquet"))
        logger.info(
            "Synthetic %s temp saved: %s (%d records)",
            "max" if is_max else "min",
            filepath.with_suffix(".parquet").name,
            len(df),
        )
        return filepath.with_suffix(".parquet")

    def download_dataset(self, dataset_key: str) -> Path:
        """Download a single dataset from configured source with synthetic fallback."""
        ds_config = self.config["datasets"][dataset_key]
        filename = ds_config["filename"]
        parquet_path = self.raw_dir / filename

        if parquet_path.exists() and parquet_path.stat().st_size > 0:
            logger.info("%s already exists at %s, skipping", dataset_key, parquet_path)
            return parquet_path

        sources = self.config.get("sources", {})
        if sources.get("primary") == "nasa_power":
            try:
                from pipeline.sources.nasa_power import fetch_nasa_power_grid

                source_config = sources["nasa_power"]
                if not hasattr(self, "_nasa_power_cache"):
                    logger.info("Fetching all datasets from NASA POWER API...")
                    self._nasa_power_cache = fetch_nasa_power_grid(
                        bounds=self.config["karnataka_bounds"],
                        start_date=self.start_date,
                        end_date=self.end_date,
                        source_config=source_config,
                    )
                if dataset_key in self._nasa_power_cache:
                    df = self._nasa_power_cache[dataset_key]
                    df.to_parquet(parquet_path)
                    logger.info("NASA POWER data saved: %s (%d records)", parquet_path.name, len(df))
                    return parquet_path
                logger.warning("NASA POWER returned no data for %s", dataset_key)
            except Exception:
                logger.warning("NASA POWER download failed, falling back to synthetic", exc_info=True)

        if dataset_key == "rainfall":
            return self._save_synthetic_rainfall(filename)
        elif dataset_key == "max_temp":
            return self._save_synthetic_temperature(filename, is_max=True)
        elif dataset_key == "min_temp":
            return self._save_synthetic_temperature(filename, is_max=False)
        else:
            raise ValueError(f"Unknown dataset key: {dataset_key}")

    def verify_checksum(
        self, filepath: Path, expected_hash: str | None = None
    ) -> bool:
        """Verify file integrity using SHA-256."""
        if not filepath.exists():
            logger.error("File not found for checksum: %s", filepath)
            return False
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()
        if expected_hash and actual_hash != expected_hash:
            logger.error(
                "Checksum mismatch for %s: expected=%s, actual=%s",
                filepath.name,
                expected_hash,
                actual_hash,
            )
            return False
        logger.info("Checksum verified for %s: %s", filepath.name, actual_hash)
        return True

    def download_all(self) -> dict[str, Path]:
        """Download all configured datasets."""
        results = {}
        for key in self.config["datasets"]:
            logger.info("Starting download for dataset: %s", key)
            results[key] = self.download_dataset(key)
        return results
