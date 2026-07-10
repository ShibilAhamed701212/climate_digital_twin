"""Feedback loop models for model improvement.

These models capture prediction errors, model corrections, and
complete feedback cycles for continuous improvement of the
digital twin's models.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class PredictionError:
    entity_id: str
    prediction_timestamp: datetime
    observation_timestamp: datetime
    prediction: dict[str, float]
    observation: dict[str, float]
    errors: dict[str, float]
    absolute_errors: dict[str, float]
    squared_errors: dict[str, float]
    model_name: str = "unknown"
    model_version: str = "0.0.0"
    forecast_horizon: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def __post_init__(self) -> None:
        var_sets = [
            ("prediction", set(self.prediction.keys())),
            ("observation", set(self.observation.keys())),
            ("errors", set(self.errors.keys())),
            ("absolute_errors", set(self.absolute_errors.keys())),
            ("squared_errors", set(self.squared_errors.keys())),
        ]
        if var_sets:
            reference_keys = var_sets[0][1]
            for name, keys in var_sets[1:]:
                if keys != reference_keys:
                    raise ValueError(
                        f"Variable keys mismatch: {var_sets[0][0]} has "
                        f"{reference_keys} but {name} has {keys}"
                    )


@dataclass
class ModelCorrection:
    model_name: str
    model_version: str
    correction_type: str
    description: str
    parameters_before: dict[str, Any]
    parameters_after: dict[str, Any]
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    trigger: str = "manual"
    applied_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied_by: str = "system"
    verification_status: str = "pending"
    correction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])


@dataclass
class FeedbackRecord:
    entity_id: str
    cycle_start: datetime
    prediction_errors: list[PredictionError]
    drift_detected: bool = False
    num_samples: int = 0
    status: str = "open"
    cycle_end: datetime | None = None
    correction: ModelCorrection | None = None
    correction_successful: bool | None = None
    drift_metrics: dict[str, float] | None = None
    notes: str = ""
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def __post_init__(self) -> None:
        if self.num_samples < 0:
            raise ValueError(f"Number of samples must be non-negative, got {self.num_samples}")


__all__ = [
    "PredictionError",
    "ModelCorrection",
    "FeedbackRecord",
]
