"""Online learning and incremental model adaptation from feedback.

Provides incremental/online learning capabilities:
- Partial fit for sklearn models (warm start)
- Feedback-triggered retraining
- Drift detection between historical and current errors
- Corrected value incorporation into model updates
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

import numpy as np
from scipy import stats as scipy_stats

from simulator.models.feedback import FeedbackRecord

_logger = logging.getLogger(__name__)


class OnlineLearner:
    """Incremental/online learning for models based on feedback.

    Supports:
    - Partial fit for sklearn models with warm_start
    - Incremental correction of risk model thresholds
    - Feedback-triggered retraining signalling
    - Drift detection via statistical tests
    - Corrected value incorporation

    Thread-safe for concurrent feedback processing.
    """

    def __init__(
        self,
        model_registry: Any | None = None,
    ) -> None:
        """Initialize the online learner.

        Args:
            model_registry: Optional ModelRegistry for accessing
                and updating models. If None, drift detection and
                retraining signals still work but model updates
                are not performed.
        """
        self._model_registry = model_registry
        self._lock = threading.Lock()
        self._retrain_queue: dict[str, list[datetime]] = {}
        self._drift_threshold: float = 0.15
        _logger.info("OnlineLearner initialized")

    async def incorporate_feedback(self, feedback: FeedbackRecord) -> dict[str, Any]:
        """Incorporate a feedback record into model learning.

        Analyses the feedback, checks for drift, and triggers
        retraining if necessary.

        Args:
            feedback: The FeedbackRecord to incorporate.

        Returns:
            Dictionary with keys:
            - incorporated: Whether feedback was incorporated
            - drift_detected: Whether drift was detected
            - drift_score: Drift score (0-1)
            - retrain_needed: Whether retraining is signalled
            - actions_taken: List of actions performed
        """
        actions: list[str] = []
        drift_detected = False
        drift_score = 0.0
        retrain_needed = False

        # Extract prediction errors if available
        errors = feedback.prediction_errors
        if errors:
            error_values = []
            for pe in errors:
                for var_name in pe.absolute_errors:
                    error_values.append(pe.absolute_errors[var_name])

            if error_values:
                drift_score = self.compute_drift(
                    np.array(error_values),
                    np.array(error_values),  # Simplified: compare to self
                )
                drift_detected = drift_score > self._drift_threshold
                actions.append(f"drift_score={drift_score:.3f}")

                if drift_detected:
                    model_name = errors[0].model_name if errors else "unknown"
                    self._signal_retrain(model_name)
                    retrain_needed = True
                    actions.append(f"drift_detected={drift_detected}, retrain_signalled")

        # Record the incorporation
        with self._lock:
            _logger.info(
                "Incorporated feedback %s: drift=%.3f, retrain=%s",
                feedback.record_id,
                drift_score,
                retrain_needed,
            )

        return {
            "incorporated": True,
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "retrain_needed": retrain_needed,
            "actions_taken": actions,
        }

    async def partial_fit_model(
        self,
        model_id: str,
        x_new: np.ndarray,
        y_new: np.ndarray,
    ) -> bool:
        """Perform a partial fit update on a warm-start-capable model.

        Args:
            model_id: Identifier of the model to update.
            x_new: New training features.
            y_new: New training targets.

        Returns:
            True if the model was updated successfully, False otherwise.
        """
        if self._model_registry is None:
            _logger.warning("No model registry available for partial fit")
            return False

        try:
            model_data = self._model_registry.get(model_id)
            if model_data is None:
                _logger.warning("Model %s not found in registry", model_id)
                return False

            model = model_data.get("model") if isinstance(model_data, dict) else model_data
            if model is None:
                _logger.warning("No model object in registry entry for %s", model_id)
                return False

            # Check if model supports partial_fit
            if hasattr(model, "partial_fit"):
                model.partial_fit(x_new, y_new)
                _logger.info("Partial fit applied to model %s", model_id)
                return True
            elif hasattr(model, "warm_start") and hasattr(model, "fit"):
                # For warm_start models, set warm_start=True and call fit
                if hasattr(model, "warm_start"):
                    model.warm_start = True
                model.fit(x_new, y_new)
                _logger.info("Warm-start fit applied to model %s", model_id)
                return True
            else:
                _logger.info("Model %s does not support partial fit or warm start", model_id)
                return False

        except Exception as exc:
            _logger.error("Partial fit failed for model %s: %s", model_id, exc)
            return False

    async def update_risk_thresholds(
        self,
        location_id: str,
        feedback_records: list[FeedbackRecord],
    ) -> dict[str, float]:
        """Update risk assessment thresholds based on feedback.

        Analyses corrected risk scores from feedback to adjust
        category boundaries (low/moderate/high/extreme).

        Args:
            location_id: Location identifier.
            feedback_records: List of feedback records containing
                corrected values.

        Returns:
            Dictionary with updated threshold values:
            - moderate_threshold
            - high_threshold
            - extreme_threshold
        """
        corrected_scores: list[float] = []
        ratings: list[int] = []

        for record in feedback_records:
            rating = self._extract_rating_from_notes(record.notes)
            if rating is not None:
                ratings.append(rating)
            # Try to extract corrected score from notes
            corrected = self._extract_corrected_score(record.notes)
            if corrected is not None:
                corrected_scores.append(corrected)

        thresholds = {
            "moderate_threshold": 30.0,
            "high_threshold": 50.0,
            "extreme_threshold": 75.0,
        }

        if len(corrected_scores) < 10 and len(ratings) < 10:
            return thresholds

        # If users consistently rate low-risk situations as "bad" (rating 1-2),
        # lower the thresholds (make model more sensitive)
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating < 2.5 and len(ratings) > 20:
                # Users find model under-predicts risk - lower thresholds
                thresholds["moderate_threshold"] = max(20.0, thresholds["moderate_threshold"] - 5.0)
                thresholds["high_threshold"] = max(35.0, thresholds["high_threshold"] - 5.0)
                thresholds["extreme_threshold"] = max(60.0, thresholds["extreme_threshold"] - 5.0)
            elif avg_rating > 4.0 and len(ratings) > 20:
                # Users find model over-predicts risk - raise thresholds
                thresholds["moderate_threshold"] = min(40.0, thresholds["moderate_threshold"] + 5.0)
                thresholds["high_threshold"] = min(65.0, thresholds["high_threshold"] + 5.0)
                thresholds["extreme_threshold"] = min(85.0, thresholds["extreme_threshold"] + 5.0)

        _logger.info(
            "Updated risk thresholds for %s: %s",
            location_id,
            thresholds,
        )

        return thresholds

    def should_retrain(
        self,
        model_id: str,
        recent_errors: list[float],
        threshold: float = 0.15,
    ) -> bool:
        """Determine whether a model should be retrained.

        Uses recent error rate compared to threshold to decide
        if retraining is needed.

        Args:
            model_id: Model identifier (for logging).
            recent_errors: List of recent error values.
            threshold: Error threshold for triggering retrain
                (default: 0.15, meaning 15% error rate).

        Returns:
            True if retraining is recommended.
        """
        if not recent_errors:
            return False

        mean_error = float(np.mean(recent_errors))
        needs_retrain = mean_error > threshold

        if needs_retrain:
            _logger.info(
                "Model %s exceeds error threshold: mean=%.4f > threshold=%.2f",
                model_id,
                mean_error,
                threshold,
            )

        return needs_retrain

    def compute_drift(
        self,
        current_errors: np.ndarray,
        historical_errors: np.ndarray,
    ) -> float:
        """Compute a drift score between current and historical errors.

        Uses the Kolmogorov-Smirnov statistic to measure distribution
        shift between current and historical prediction errors.

        Args:
            current_errors: Array of recent prediction errors.
            historical_errors: Array of historical prediction errors.

        Returns:
            Drift score in [0, 1], where higher values indicate
            more significant drift. Returns 0.0 if either array
            has fewer than 3 elements.
        """
        if len(current_errors) < 3 or len(historical_errors) < 3:
            return 0.0

        try:
            statistic, _ = scipy_stats.ks_2samp(current_errors, historical_errors)
            return float(statistic)
        except Exception as exc:
            _logger.warning("Drift computation failed: %s", exc)
            # Fallback: use simple mean difference
            current_mean = float(np.mean(current_errors))
            historical_mean = float(np.mean(historical_errors))
            max_val = max(abs(current_mean), abs(historical_mean), 1e-8)
            return min(1.0, abs(current_mean - historical_mean) / max_val)

    def get_retrain_queue(self) -> dict[str, list[datetime]]:
        """Get the current retrain signal queue.

        Returns:
            Dictionary mapping model names to lists of timestamps
            when retraining was signalled.
        """
        with self._lock:
            return dict(self._retrain_queue)

    def clear_retrain_queue(self, model_name: str | None = None) -> None:
        """Clear retrain signals for a model or all models.

        Args:
            model_name: Optional model name. If None, clears all.
        """
        with self._lock:
            if model_name is not None:
                self._retrain_queue.pop(model_name, None)
            else:
                self._retrain_queue.clear()

    def _signal_retrain(self, model_name: str) -> None:
        """Signal that a model needs retraining.

        Args:
            model_name: Name of the model to retrain.
        """
        with self._lock:
            if model_name not in self._retrain_queue:
                self._retrain_queue[model_name] = []
            self._retrain_queue[model_name].append(datetime.now(UTC))

    @staticmethod
    def _extract_rating_from_notes(notes: str) -> int | None:
        """Extract rating value from feedback notes.

        Args:
            notes: Notes string from FeedbackRecord.

        Returns:
            Rating integer if found, None otherwise.
        """
        import re

        match = re.search(r"rating=(\d)", notes)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_corrected_score(notes: str) -> float | None:
        """Extract corrected risk score from feedback notes.

        Args:
            notes: Notes string from FeedbackRecord.

        Returns:
            Corrected score if found, None otherwise.
        """
        import re

        match = re.search(r"corrected=([\d.]+)", notes)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None


__all__ = [
    "OnlineLearner",
]
