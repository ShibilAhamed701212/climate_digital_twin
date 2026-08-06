from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pipeline.providers.fetch_result import FetchResult
from pipeline.providers.manager import Observation

_logger = logging.getLogger(__name__)


@dataclass
class Manifest:
    run_id: str
    provider: str
    status: str
    requested_at: str
    completed_at: str
    records_received: int
    records_normalized: int
    records_validated: int
    records_rejected: int
    records_persisted: int
    synthetic_count: int
    error: str | None = None
    paths: dict[str, str | None] | None = None


class ManifestWriter:
    def __init__(self, base_dir: str | Path = "data") -> None:
        self._base_dir = Path(base_dir)
        self._manifests_dir = self._base_dir / "manifests"
        self._manifests_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        run_id: str,
        fetch_result: FetchResult,
        valid: list[Observation],
        rejected: list[Observation],
        raw_path: str | None = None,
        normalized_path: str | None = None,
        validated_path: str | None = None,
        rejected_path: str | None = None,
    ) -> Manifest:
        synthetic_count = sum(
            1 for o in valid + rejected if getattr(o, "authenticity", "") == "SYNTHETIC"
        )
        manifest = Manifest(
            run_id=run_id,
            provider=fetch_result.provider.value if fetch_result.provider else "",
            status=fetch_result.status,
            requested_at=fetch_result.requested_at.isoformat() if fetch_result.requested_at else "",
            completed_at=fetch_result.completed_at.isoformat() if fetch_result.completed_at else "",
            records_received=len(fetch_result.observations),
            records_normalized=len(valid) + len(rejected),
            records_validated=len(valid),
            records_rejected=len(rejected),
            records_persisted=len(valid),
            synthetic_count=synthetic_count,
            error=fetch_result.error_message,
            paths={
                "raw": raw_path,
                "normalized": normalized_path,
                "validated": validated_path,
                "rejected": rejected_path,
                "manifest": str(self._manifests_dir / f"{run_id}.json"),
            },
        )
        filepath = self._manifests_dir / f"{run_id}.json"
        filepath.write_text(
            json.dumps(
                {
                    "run_id": manifest.run_id,
                    "run_timestamp": manifest.completed_at,
                    "provider": manifest.provider,
                    "status": manifest.status,
                    "records_received": manifest.records_received,
                    "records_normalized": manifest.records_normalized,
                    "records_validated": manifest.records_validated,
                    "records_rejected": manifest.records_rejected,
                    "records_persisted": manifest.records_persisted,
                    "synthetic_count": manifest.synthetic_count,
                    "error": manifest.error,
                    "paths": manifest.paths,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        _logger.info("Manifest written to %s", filepath)
        return manifest
