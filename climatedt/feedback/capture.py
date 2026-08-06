"""Feedback capture — persists user ratings for analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CapturedFeedback:
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    status: str = "captured"
    feedback_type: str = "general"
    location_id: str = ""
    rating: float = 0.0
    comment: str = ""
    reference_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dashboard_row(self) -> dict[str, Any]:
        return {
            "date": self.created_at,
            "location": self.location_id or "unknown",
            "rating": float(self.rating),
            "type": self.feedback_type,
            "comment": self.comment,
            "record_id": self.record_id,
        }


class FeedbackCaptureService:
    def __init__(self, store: Any | None = None) -> None:
        from climatedt.feedback.storage import FeedbackStore

        self._store = store if store is not None else FeedbackStore()

    @property
    def store(self) -> Any:
        return self._store

    async def capture_risk_feedback(
        self,
        assessment_id: str,
        rating: float,
        corrected_risk_score: float | None = None,
        comment: str = "",
    ) -> CapturedFeedback:
        note = comment
        if corrected_risk_score is not None:
            note = f"{comment} corrected_score={corrected_risk_score}".strip()
        record = CapturedFeedback(
            feedback_type="risk",
            location_id=assessment_id,
            rating=float(rating),
            comment=note,
            reference_id=assessment_id,
        )
        self._store.save(record)
        return record

    async def capture_forecast_feedback(
        self,
        forecast_id: str,
        rating: float,
        observed_values: dict[str, float] | None = None,
        comment: str = "",
    ) -> CapturedFeedback:
        note = comment
        if observed_values:
            note = f"{comment} observed={observed_values}".strip()
        record = CapturedFeedback(
            feedback_type="forecast",
            location_id=forecast_id,
            rating=float(rating),
            comment=note,
            reference_id=forecast_id,
        )
        self._store.save(record)
        return record

    async def capture_general_feedback(
        self,
        location_id: str,
        feedback_type: str,
        rating: float,
        comment: str = "",
    ) -> CapturedFeedback:
        record = CapturedFeedback(
            feedback_type=feedback_type or "general",
            location_id=location_id,
            rating=float(rating),
            comment=comment,
            reference_id=location_id,
        )
        self._store.save(record)
        return record
