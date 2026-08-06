"""Forecast provenance — every forecast knows where it came from.

A ForecastResult is produced when a validated model generates a forecast
for a twin location. It carries full provenance so consumers can verify
the model, training run, and data that produced the prediction.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ForecastResult:
    location_id: str = ""
    timestamp: str = ""
    rainfall: float = 0.0
    max_temp: float = 0.0
    min_temp: float = 0.0
    confidence: float = 0.0
    model_id: str = ""
    training_run_id: str = ""
    model_architecture: str = ""
    dataset_id: str = ""
    authenticity: str = ""
    horizon_days: int = 1
    source_twin_version: int = 0
    physics_validated: bool = True
    forecast_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForecastResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ForecastStore:
    def __init__(self, path: str = "data/forecasts/forecast_history.jsonl"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, result: ForecastResult) -> None:
        with open(self._path, "a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")

    def list_recent(self, limit: int = 10) -> list[ForecastResult]:
        if not self._path.exists():
            return []
        with open(self._path) as f:
            lines = [line.strip() for line in f if line.strip()]
        recent = [ForecastResult.from_dict(json.loads(line)) for line in lines[-limit:]]
        return list(reversed(recent))
