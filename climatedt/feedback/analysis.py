"""Feedback analytics over the shared feedback store."""

from __future__ import annotations

from collections import Counter
from statistics import mean, pstdev
from typing import Any


class FeedbackAnalyzer:
    def __init__(self, feedback_store: Any) -> None:
        self._store = feedback_store

    def _rows(self) -> list[Any]:
        return list(self._store.list_all())

    async def get_overview_stats(self) -> dict[str, Any]:
        rows = self._rows()
        ratings = [float(getattr(r, "rating", 0) or 0) for r in rows]
        type_counts = Counter(str(getattr(r, "feedback_type", "general") or "general") for r in rows)
        rating_counts = Counter(int(round(r)) for r in ratings if r > 0)
        return {
            "total_feedback": len(rows),
            "avg_rating": float(mean(ratings)) if ratings else 0.0,
            "rating_std": float(pstdev(ratings)) if len(ratings) > 1 else 0.0,
            "rating_counts": {str(k): v for k, v in sorted(rating_counts.items())},
            "feedback_types": dict(type_counts),
        }

    async def get_improvement_trend(self, _days: int = 90) -> dict[str, Any]:
        rows = self._rows()
        ratings = [float(getattr(r, "rating", 0) or 0) for r in rows]
        if len(ratings) < 2:
            return {
                "overall_trend": 0.0,
                "first_period_avg": 0.0,
                "second_period_avg": 0.0,
                "trend_direction": "insufficient_data",
                "improvement_pct": 0.0,
            }
        half = len(ratings) // 2
        first = mean(ratings[:half]) if half else mean(ratings)
        second = mean(ratings[half:]) if ratings[half:] else first
        improvement = ((second - first) / first * 100.0) if first else 0.0
        direction = "improving" if second > first else "declining" if second < first else "stable"
        return {
            "overall_trend": float(second - first),
            "first_period_avg": float(first),
            "second_period_avg": float(second),
            "trend_direction": direction,
            "improvement_pct": float(improvement),
        }

    async def get_location_performance(self, location_id: str) -> dict[str, Any]:
        rows = [
            r
            for r in self._rows()
            if str(getattr(r, "location_id", "")) == location_id
            or str(getattr(r, "reference_id", "")) == location_id
        ]
        ratings = [float(getattr(r, "rating", 0) or 0) for r in rows]
        if not ratings:
            return {
                "total_feedback": 0,
                "avg_rating": 0.0,
                "trend": "insufficient_data",
                "recent_avg": None,
            }
        recent = mean(ratings[-5:]) if ratings else None
        return {
            "total_feedback": len(rows),
            "avg_rating": float(mean(ratings)),
            "trend": "stable",
            "recent_avg": float(recent) if recent is not None else None,
        }

    def list_dashboard_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self._rows():
            if hasattr(record, "to_dashboard_row"):
                rows.append(record.to_dashboard_row())
            else:
                rows.append(
                    {
                        "date": getattr(record, "created_at", ""),
                        "location": getattr(record, "location_id", "unknown"),
                        "rating": float(getattr(record, "rating", 0) or 0),
                        "type": getattr(record, "feedback_type", "general"),
                        "comment": getattr(record, "comment", ""),
                        "record_id": getattr(record, "record_id", ""),
                    }
                )
        return rows
