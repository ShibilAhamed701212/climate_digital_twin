from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from disaster_intelligence.config import data_dir, load_disaster_config

logger = logging.getLogger(__name__)


def _secure_unlink(path: Path) -> None:
    try:
        if path.is_file():
            size = path.stat().st_size
            with path.open("r+b") as fh:
                fh.write(b"\x00" * min(size, 1024 * 1024))
                fh.flush()
                os.fsync(fh.fileno())
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to remove %s: %s", path, exc)


def apply_ttl() -> int:
    cfg = load_disaster_config()
    ttl_days = float(cfg.get("ttl_days") or 90)
    cache_hours = float(cfg.get("stac_cache_hours") or 6)
    cutoff = time.time() - ttl_days * 86400
    cache_cutoff = time.time() - cache_hours * 3600
    root = data_dir()
    removed = 0
    for folder in (root / "cogs", root / "geojson", root / "tmp"):
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            mtime = path.stat().st_mtime
            stale_part = path.suffix == ".part"
            stale_cache = "stac_cache" in path.parts and mtime < cache_cutoff
            stale_ttl = mtime < cutoff
            if stale_part or stale_cache or stale_ttl:
                _secure_unlink(path)
                removed += 1
    logger.info("TTL janitor removed %s expired disaster artifacts", removed)
    return removed
