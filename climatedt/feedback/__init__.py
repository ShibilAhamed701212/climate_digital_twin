"""Feedback loop and adaptive learning for model improvement.

This package provides a complete feedback system that:
- Collects user feedback on risk assessments and forecasts
- Stores feedback persistently using Parquet-based storage
- Adapts model weights based on feedback patterns
- Supports online/incremental learning for models
- Provides analytics on feedback trends and model improvement
"""

from __future__ import annotations

from climatedt.feedback.adaptation import WeightAdaptation
from climatedt.feedback.analysis import FeedbackAnalyzer
from climatedt.feedback.capture import FeedbackCaptureService
from climatedt.feedback.online_learning import OnlineLearner
from climatedt.feedback.storage import FeedbackStore

__all__ = [
    "FeedbackCaptureService",
    "FeedbackStore",
    "WeightAdaptation",
    "OnlineLearner",
    "FeedbackAnalyzer",
]
