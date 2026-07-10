"""Weight adaptation based on feedback patterns.

Adapts model ensemble weights dynamically based on:
- Performance-based: Models with positive feedback get higher weights
- Recency-weighted: Recent feedback matters more than old feedback
- Location-specific: Different weights per region
- Seasonal: Different weights per season
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from simulator.models.feedback import FeedbackRecord

_logger = logging.getLogger(__name__)


class WeightAdaptation:
    """Adapts model weights based on feedback patterns.

    Supports multiple adaptation strategies:
    - Performance-based weighting from feedback ratings
    - Recency-weighted exponential decay
    - Location-specific weight computation
    - Seasonal weight adjustment

    Thread-safe when used with thread-safe model registry and feedback store.
    """

    def __init__(
        self,
        model_registry: Any | None = None,
        feedback_store: Any | None = None,
    ) -> None:
        """Initialize the weight adaptation system.

        Args:
            model_registry: Optional ModelRegistry for accessing model
                metadata. If None, weights are computed from feedback alone.
            feedback_store: Optional FeedbackStore for retrieving feedback
                records. If None, weights must be provided directly.
        """
        self._model_registry = model_registry
        self._feedback_store = feedback_store
        self._default_weights: dict[str, float] = {
            "lstm": 0.25,
            "xgboost": 0.25,
            "prophet": 0.25,
            "ensemble": 0.25,
        }

    async def update_ensemble_weights(
        self,
        location_id: str | None = None,
        season: str | None = None,
    ) -> dict[str, float]:
        """Update ensemble model weights based on feedback.

        Computes performance-based weights for each model using
        available feedback. Falls back to default weights when
        insufficient feedback exists.

        Args:
            location_id: Optional location for location-specific weights.
            season: Optional season for seasonal weighting.

        Returns:
            Dictionary mapping model names to normalized weights
            that sum to approximately 1.0.
        """
        feedback_records: list[FeedbackRecord] = []

        if self._feedback_store is not None and location_id is not None:
            try:
                feedback_records = await self._feedback_store.query_feedback(
                    location_id=location_id,
                    limit=1000,
                )
            except Exception as exc:
                _logger.warning("Failed to query feedback: %s", exc)

        if not feedback_records:
            _logger.info(
                "No feedback available for location=%s, using default weights",
                location_id,
            )
            return dict(self._default_weights)

        performance_scores = self.compute_performance_score(feedback_records)
        weights = self._normalize_weights(performance_scores)

        if season is not None:
            weights = self._apply_seasonal_adjustment(weights, season)

        _logger.info(
            "Updated ensemble weights for location=%s, season=%s: %s",
            location_id,
            season,
            weights,
        )

        return weights

    async def get_current_weights(
        self,
        location_id: str | None = None,
    ) -> dict[str, float]:
        """Get the current model weights for a location.

        Returns default weights if no feedback-driven weights
        have been computed.

        Args:
            location_id: Optional location identifier.

        Returns:
            Dictionary of current model weights.
        """
        if location_id is not None and self._feedback_store is not None:
            try:
                feedback_records = await self._feedback_store.query_feedback(
                    location_id=location_id, limit=100
                )
                if feedback_records:
                    scores = self.compute_performance_score(feedback_records)
                    return self._normalize_weights(scores)
            except Exception:
                pass

        return dict(self._default_weights)

    def compute_performance_score(
        self,
        feedback_records: list[FeedbackRecord],
    ) -> dict[str, float]:
        """Compute performance scores for each model from feedback.

        Extracts model names from feedback notes and computes
        weighted average ratings for each model.

        Args:
            feedback_records: List of FeedbackRecord objects
                containing ratings in their notes.

        Returns:
            Dictionary mapping model names to performance scores
            in [0, 1] range.
        """
        model_ratings: dict[str, list[tuple[float, float]]] = {}

        for record in feedback_records:
            model_name = self._extract_model_name(record.notes)
            rating = self._extract_rating(record.notes)

            if model_name is None or rating is None:
                continue

            if model_name not in model_ratings:
                model_ratings[model_name] = []

            # Apply recency weighting
            days_ago = (datetime.now(UTC) - record.cycle_start).days
            recency_weight = self.exponential_decay_weight(max(0, days_ago))
            # Normalize rating from 1-5 to 0-1
            normalized_rating = (rating - 1) / 4.0
            model_ratings[model_name].append((normalized_rating, recency_weight))

        if not model_ratings:
            return dict(self._default_weights)

        scores: dict[str, float] = {}
        for model_name, ratings_and_weights in model_ratings.items():
            total_weight = sum(w for _, w in ratings_and_weights)
            if total_weight > 0:
                weighted_sum = sum(r * w for r, w in ratings_and_weights)
                scores[model_name] = weighted_sum / total_weight
            else:
                scores[model_name] = 0.5

        return scores

    @staticmethod
    def exponential_decay_weight(days_ago: int, half_life: int = 30) -> float:
        """Compute an exponential decay weight based on age.

        Uses the formula: weight = 2^(-days_ago / half_life)

        Args:
            days_ago: Number of days since the event.
            half_life: Half-life in days (default: 30).

        Returns:
            Decay weight in [0, 1] range. Returns 0.0 for negative
            days_ago.
        """
        if days_ago < 0:
            return 0.0
        if half_life <= 0:
            return 1.0
        return 2.0 ** (-days_ago / half_life)

    @staticmethod
    def _normalize_weights(scores: dict[str, float]) -> dict[str, float]:
        """Normalize a dictionary of scores to sum to 1.0.

        Args:
            scores: Dictionary mapping names to raw scores.

        Returns:
            Dictionary with normalized weights summing to ~1.0.
        """
        total = sum(scores.values())
        if total <= 0:
            n = len(scores)
            return {k: 1.0 / n for k in scores}
        return {k: v / total for k, v in scores.items()}

    @staticmethod
    def _extract_model_name(notes: str) -> str | None:
        """Extract a model name from feedback notes.

        Looks for patterns like 'model=lstm', 'model=xgboost', etc.

        Args:
            notes: The notes string from a FeedbackRecord.

        Returns:
            Extracted model name, or None if not found.
        """
        match = re.search(r"model=(\w+)", notes)
        if match:
            return match.group(1)
        # Try to infer from context
        for model in ["lstm", "xgboost", "prophet", "ensemble"]:
            if model in notes.lower():
                return model
        return None

    @staticmethod
    def _extract_rating(notes: str) -> int | None:
        """Extract a rating value from feedback notes.

        Looks for patterns like 'rating=5', 'rating=3', etc.

        Args:
            notes: The notes string from a FeedbackRecord.

        Returns:
            Extracted rating integer, or None if not found.
        """
        match = re.search(r"rating=(\d)", notes)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _apply_seasonal_adjustment(
        weights: dict[str, float],
        season: str,
    ) -> dict[str, float]:
        """Apply seasonal adjustments to model weights.

        Different models perform better in different seasons:
        - Summer: LSTM may perform better (captures heat waves)
        - Monsoon: Prophet may perform better (seasonal patterns)
        - Winter: XGBoost may perform better (stable patterns)

        Args:
            weights: Current model weights.
            season: Season name ('spring', 'summer', 'autumn', 'winter').

        Returns:
            Adjusted weights (still normalized).
        """
        adjustments: dict[str, dict[str, float]] = {
            "summer": {"lstm": 1.3, "prophet": 0.8, "xgboost": 0.9, "ensemble": 1.0},
            "winter": {"lstm": 0.8, "prophet": 0.9, "xgboost": 1.2, "ensemble": 1.1},
            "spring": {"lstm": 0.9, "prophet": 1.1, "xgboost": 1.0, "ensemble": 1.0},
            "autumn": {"lstm": 1.0, "prophet": 1.2, "xgboost": 0.9, "ensemble": 0.9},
        }

        season_adjust = adjustments.get(season.lower(), {})
        if not season_adjust:
            return weights

        adjusted: dict[str, float] = {}
        for model, weight in weights.items():
            factor = season_adjust.get(model, 1.0)
            adjusted[model] = weight * factor

        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}

        return adjusted


__all__ = [
    "WeightAdaptation",
]
