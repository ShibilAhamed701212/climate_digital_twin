from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG: dict[str, Any] | None = None


def _config_path() -> Path:
    env = os.environ.get("DISASTER_CONFIG_PATH")
    if env:
        return Path(env)
    return Path("config/disaster_config.yaml")


def load_disaster_config() -> dict[str, Any]:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    path = _config_path()
    if not path.exists():
        _CONFIG = {}
        return _CONFIG
    with path.open(encoding="utf-8") as fh:
        _CONFIG = yaml.safe_load(fh) or {}
    return _CONFIG


def reset_disaster_config() -> None:
    global _CONFIG
    _CONFIG = None


def data_dir() -> Path:
    raw = os.environ.get("DISASTER_DATA_DIR", "data/disaster")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def env_flag(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
