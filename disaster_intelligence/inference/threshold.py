from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from disaster_intelligence.domain.entities import InferenceResult
from disaster_intelligence.domain.enums import QualityFlag
from disaster_intelligence.domain.geotiff import read_uint8_tiff


class S1ThresholdFloodRunner:
    """CPU flood mask: pixels darker than dn_max (or SAR dB threshold mapped to DN)."""

    model_id = "s1-threshold-v0"
    model_version = "0"
    confidence_type = "threshold_boundary_agreement"
    runtime_name = "numpy"
    fallback_used = False
    checkpoint_sha256 = ""
    device = "cpu"

    def __init__(self, dn_max: int = 80, requested: str = "threshold") -> None:
        self._dn_max = dn_max
        self._requested = requested

    def provenance(self) -> dict[str, str]:
        return {
            "flood": self.model_id,
            "requested": self._requested,
            "requested_model": self._requested,
            "actual_model": self.model_id,
            "runtime": self.runtime_name,
            "device": self.device,
            "checkpoint_sha256": self.checkpoint_sha256,
            "confidence_type": self.confidence_type,
            "fallback": "threshold" if self.fallback_used else "none",
            "fallback_used": "true" if self.fallback_used else "false",
            "fallback_reason": "",
            "sensor": "sentinel-1",
            "polarization": "uint8-dn",
            "input_channels": "1",
            "processing_ms": "0",
        }

    def run(self, task: str, mask_or_path: Any, **kwargs: Any) -> InferenceResult:
        start = time.perf_counter()
        if task != "flood_extent":
            raise ValueError(f"Unsupported task {task}")
        if isinstance(mask_or_path, list):
            mask = mask_or_path
        else:
            rows, _, _ = read_uint8_tiff(Path(str(mask_or_path)))
            mask = [[1 if v <= self._dn_max else 0 for v in row] for row in rows]
            if kwargs.get("invert") is False:
                mask = [[1 if v > self._dn_max else 0 for v in row] for row in rows]
        water = sum(1 for row in mask for v in row if v > 0)
        total = sum(len(row) for row in mask) or 1
        duration = (time.perf_counter() - start) * 1000
        return InferenceResult(
            task=task,
            metrics={"water_pct": water / total, "water_pixels": water, "total_pixels": total},
            output_uris=[],
            duration_ms=duration,
            quality_flags=[QualityFlag.S1_ONLY.value],
        )

    def mask_from_rows(self, rows: list[list[int]]) -> list[list[int]]:
        return [[1 if v <= self._dn_max else 0 for v in row] for row in rows]

    def mask_from_path(self, path: str) -> list[list[int]]:
        rows, _, _ = read_uint8_tiff(Path(path))
        return self.mask_from_rows(rows)

    def boundary_confidence(self, rows: list[list[int]], margin: int = 8) -> float | None:
        """Share of pixels farther than `margin` DN from the threshold (not a calibrated score)."""
        total = 0
        decisive = 0
        for row in rows:
            for value in row:
                total += 1
                if abs(int(value) - self._dn_max) > margin:
                    decisive += 1
        if total == 0:
            return None
        return round(decisive / total, 4)
