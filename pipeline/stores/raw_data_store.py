from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from simulator.models.weather import DataSource

_logger = logging.getLogger(__name__)


class RawDataStore:
    def __init__(self, base_dir: str | Path = "data/real") -> None:
        self._base_dir = Path(base_dir)

    def save(
        self,
        provider: DataSource,
        run_id: str,
        response_body: str,
        request_params: dict[str, Any] | None = None,
        endpoint: str = "",
        http_status: int = 0,
        coordinates: tuple[float, float] | None = None,
    ) -> Path:
        provider_dir = self._base_dir / "raw" / provider.value
        provider_dir.mkdir(parents=True, exist_ok=True)
        checksum = hashlib.sha256(response_body.encode("utf-8")).hexdigest()
        metadata = {
            "provider": provider.value,
            "run_id": run_id,
            "endpoint": endpoint,
            "request_params": request_params or {},
            "http_status": http_status,
            "coordinates": coordinates,
            "retrieval_timestamp": datetime.now(UTC).isoformat(),
            "response_sha256": checksum,
        }
        record = {"metadata": metadata, "response": response_body}
        filepath = provider_dir / f"{run_id}.json"
        filepath.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        _logger.info("Raw response saved to %s (%d bytes)", filepath, len(response_body))
        return filepath
