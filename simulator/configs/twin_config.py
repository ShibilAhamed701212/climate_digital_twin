"""Configuration for Digital Twin simulator modules.

Provides default paths, data source URLs, and logging configuration.
All settings can be overridden via environment variables or the configure() function.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

_logger = logging.getLogger(__name__)


@dataclass
class ClimateDTConfig:
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CLIMATEDT_DATA_DIR", "~/.climatedt/data")
        ).expanduser()
    )
    observations_dir: str = "observations"
    twin_state_dir: str = "twin_state"
    datasets_dir: str = "datasets"
    features_dir: str = "features"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    imd_base_url: str = "https://api.data.gov.in/resource"
    era5_cds_url: str = "https://cds.climate.copernicus.eu/api"
    noaa_ncei_base_url: str = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    parquet_compression: str = "snappy"
    parquet_row_group_size: int = 65536
    max_versions_per_location: int = 1000
    version_index_name: str = "version_index.parquet"
    feature_registry_name: str = "feature_registry.parquet"
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


_config: ClimateDTConfig | None = None


def get_config() -> ClimateDTConfig:
    global _config
    if _config is None:
        _config = ClimateDTConfig()
        _configure_logging(_config)
    return _config


def configure(**kwargs) -> ClimateDTConfig:
    global _config
    existing = get_config()
    for key, value in kwargs.items():
        if not hasattr(existing, key):
            raise TypeError(f"Unknown configuration option: {key}")
        if key.endswith("_dir") and isinstance(value, str):
            value = Path(value)
        setattr(existing, key, value)
    _configure_logging(existing)
    return existing


def get_data_dir() -> Path:
    config = get_config()
    data_dir = config.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _configure_logging(config: ClimateDTConfig) -> None:
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format=config.log_format,
        force=False,
    )


def resolve_subdir(subdir: str) -> Path:
    data_dir = get_data_dir()
    path = (data_dir / subdir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "ClimateDTConfig",
    "get_config",
    "configure",
    "get_data_dir",
    "resolve_subdir",
]
