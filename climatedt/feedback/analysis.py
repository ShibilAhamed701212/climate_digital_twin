from typing import Any


class FeedbackAnalyzer:
    def __init__(self, feedback_store: Any) -> None:
        self._store = feedback_store

    async def get_overview_stats(self) -> dict[str, Any]:
        return {
            "total_feedback": 0,
            "avg_rating": 0.0,
            "rating_std": 0.0,
            "rating_counts": {},
            "feedback_types": {},
        }

    async def get_improvement_trend(self, _days: int = 90) -> dict[str, Any]:
        return {
            "overall_trend": 0.0,
            "first_period_avg": 0.0,
            "second_period_avg": 0.0,
            "trend_direction": "insufficient_data",
            "improvement_pct": 0.0,
        }

    async def get_location_performance(self, _location_id: str) -> dict[str, Any]:
        return {
            "total_feedback": 0,
            "avg_rating": 0.0,
            "trend": "insufficient_data",
            "recent_avg": None,
        }
