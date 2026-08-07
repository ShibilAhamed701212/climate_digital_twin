"""HistoricalStore — reads bundled archived climate datasets.

Historical datasets are distributed with the repository and are never
overwritten. They serve as the HISTORICAL data state fallback when no
LIVE or CACHED observation is available.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pipeline.providers.manager import Observation, ObservationStatus

logger = logging.getLogger(__name__)


class HistoricalStore:
    """Reads bundled parquet datasets and returns them as HISTORICAL observations."""

    # Maps variable name to parquet filename stem
    VARIABLE_FILE_MAP: dict[str, str] = {
        "temperature_2m": "maxtemp",
        "temperature_2m_min": "mintemp",
        "precipitation_mm": "rainfall",
        "rainfall": "rainfall",
        "max_temp": "maxtemp",
        "min_temp": "mintemp",
    }

    # Maps variable name to parquet column name
    VARIABLE_COLUMN_MAP: dict[str, str] = {
        "temperature_2m": "MaxTemp",
        "temperature_2m_min": "MinTemp",
        "precipitation_mm": "Rainfall",
        "rainfall": "Rainfall",
        "max_temp": "MaxTemp",
        "min_temp": "MinTemp",
    }

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            # Resolve relative to project root (3 levels up from this file)
            _project_root = Path(__file__).resolve().parent.parent.parent
            self._data_dir = _project_root / "data" / "raw"
        self._datasets: dict[str, pd.DataFrame] = {}

    def lookup(
        self, location_id: str, variable: str, _timestamp: str | None = None
    ) -> Observation | None:
        """Look up a historical observation.

        Returns an Observation with status HISTORICAL if data exists,
        None otherwise.
        """
        file_stem = self.VARIABLE_FILE_MAP.get(variable)
        if file_stem is None:
            return None

        df = self._load_dataset(file_stem)
        if df is None or df.empty:
            return None

        col = self.VARIABLE_COLUMN_MAP.get(variable, variable)
        if col not in df.columns:
            return None

        sub_df = df
        lat_lon = self._resolve_lat_lon(location_id)
        if lat_lon is not None and "Latitude" in df.columns and "Longitude" in df.columns:
            target_lat, target_lon = lat_lon
            lats = df["Latitude"].unique()
            lons = df["Longitude"].unique()
            c_lat = min(lats, key=lambda x: abs(x - target_lat))
            c_lon = min(lons, key=lambda x: abs(x - target_lon))
            matched = df[(df["Latitude"] == c_lat) & (df["Longitude"] == c_lon)]
            if not matched.empty:
                sub_df = matched

        # Use the most recent row as the current observation
        latest = sub_df.iloc[-1]
        value = float(latest[col])

        return Observation(
            status=ObservationStatus.HISTORICAL,
            provider="NASA POWER",
            observation_timestamp=str(latest.get("Date", "")),
            retrieved_timestamp=datetime.now(UTC).isoformat(),
            age_seconds=0.0,
            confidence=0.85,
            data_source_identifier="nasa_power_v2.3.8",
            dataset_version="1981-2023_archive_v1",
            values={variable: value},
            location_id=location_id,
            variable=variable,
        )

    def _resolve_lat_lon(self, location_id: str) -> tuple[float, float] | None:
        """Resolve location_id to (latitude, longitude)."""
        try:
            from pipeline.sources.location_registry import LocationRegistry

            registry = LocationRegistry()
            coords = registry.get_coordinates(location_id)
            if coords:
                return (coords[0], coords[1])
        except Exception:
            pass

        try:
            from dashboard.config.config import SAMPLE_LOCATIONS

            for loc in SAMPLE_LOCATIONS:
                if loc["id"] == location_id:
                    return (loc["lat"], loc["lon"])
        except Exception:
            pass

        return None

    def _load_dataset(self, file_stem: str) -> pd.DataFrame | None:
        if file_stem in self._datasets:
            return self._datasets[file_stem]

        file_path = self._data_dir / f"{file_stem}.parquet"

        if file_path.exists():
            try:
                df = pd.read_parquet(file_path)
                self._datasets[file_stem] = df
                logger.info("Loaded historical dataset %s (%d rows)", file_path, len(df))
                return df
            except Exception as e:
                logger.warning("Failed to load historical dataset %s: %s", file_path, e)
                return None

        logger.warning("Historical dataset not found: %s", file_stem)
        return None

    def is_available(self) -> bool:
        return any(self._load_dataset(k) is not None for k in set(self.VARIABLE_FILE_MAP.values()))
