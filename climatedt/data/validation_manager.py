"""Phase 12.5 — Validation Dataset Manager.

Manages download, caching, verification, and provenance tracking for
scientific validation datasets: ERA5, NASA POWER, CHIRPS, SMAP, IMD, CWC.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_VALIDATION_DIR = Path("data/validation")

MANIFEST_FILENAME = "dataset_manifest.json"


class ValidationDatasetManager:
    """Manages acquisition and provenance of validation datasets."""

    def __init__(self, base_dir: str | Path = DATA_VALIDATION_DIR) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _manifest_path(self, dataset_id: str) -> Path:
        return self._base / dataset_id / MANIFEST_FILENAME

    def register_dataset(
        self,
        dataset_id: str,
        provider: str,
        variables: list[str],
        source_url: str,
        spatial_resolution: str = "",
        temporal_resolution: str = "",
        license_info: str = "",
        **extra: str,
    ) -> dict[str, Any]:
        """Record dataset metadata with full provenance."""
        ds_dir = self._base / dataset_id
        ds_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "dataset_id": dataset_id,
            "provider": provider,
            "variables": variables,
            "source_url": source_url,
            "spatial_resolution": spatial_resolution,
            "temporal_resolution": temporal_resolution,
            "license": license_info,
            "registered_at": datetime.now(UTC).isoformat(),
            "authenticity": "REAL",
            "quality": "raw",
            **extra,
        }
        with open(ds_dir / MANIFEST_FILENAME, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest

    def record_download(
        self,
        dataset_id: str,
        filename: str,
        file_size_bytes: int | None = None,
        download_url: str = "",
    ) -> dict[str, Any]:
        """Record a downloaded file with checksum verification."""
        ds_dir = self._base / dataset_id
        file_path = ds_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Downloaded file not found: {file_path}")

        sha256 = self._compute_sha256(file_path)
        file_size = file_size_bytes or file_path.stat().st_size

        record = {
            "filename": filename,
            "file_size_bytes": file_size,
            "sha256_prefix": sha256[:16],
            "sha256_full": sha256,
            "downloaded_at": datetime.now(UTC).isoformat(),
            "download_url": download_url,
        }

        manifest_path = self._manifest_path(dataset_id)
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest = {"dataset_id": dataset_id}

        manifest.setdefault("files", []).append(record)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return record

    def verify_file(self, dataset_id: str, filename: str) -> bool:
        """Verify a file against its stored checksum."""
        manifest_path = self._manifest_path(dataset_id)
        if not manifest_path.exists():
            return False

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        file_path = self._base / dataset_id / filename
        if not file_path.exists():
            return False

        current_sha = self._compute_sha256(file_path)
        for rec in manifest.get("files", []):
            if rec.get("filename") == filename:
                return current_sha == rec.get("sha256_full", "")
        return False

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def list_datasets(self) -> list[str]:
        """List registered datasets."""
        if not self._base.exists():
            return []
        return [
            d.name for d in self._base.iterdir() if d.is_dir() and (d / MANIFEST_FILENAME).exists()
        ]
