import uuid


class _FeedbackRecord:
    def __init__(self) -> None:
        self.record_id = uuid.uuid4().hex[:16]
        self.status = "captured"


class FeedbackCaptureService:
    def __init__(self) -> None:
        self._records: list[_FeedbackRecord] = []

    async def capture_risk_feedback(
        self,
        _assessment_id: str,
        _rating: float,
        _corrected_risk_score: float | None = None,
        _comment: str = "",
    ) -> _FeedbackRecord:
        record = _FeedbackRecord()
        self._records.append(record)
        return record

    async def capture_forecast_feedback(
        self,
        _forecast_id: str,
        _rating: float,
        _observed_values: dict[str, float] | None = None,
        _comment: str = "",
    ) -> _FeedbackRecord:
        record = _FeedbackRecord()
        self._records.append(record)
        return record

    async def capture_general_feedback(
        self,
        _location_id: str,
        _feedback_type: str,
        _rating: float,
        _comment: str = "",
    ) -> _FeedbackRecord:
        record = _FeedbackRecord()
        self._records.append(record)
        return record
