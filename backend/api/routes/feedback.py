from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_feedback_analyzer, get_feedback_capture
from backend.api.models import (
    FeedbackResponse,
    FeedbackStatsResponse,
    FeedbackTrendResponse,
    LocationFeedbackResponse,
    SubmitForecastFeedbackRequest,
    SubmitGeneralFeedbackRequest,
    SubmitRiskFeedbackRequest,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "/risk",
    response_model=FeedbackResponse,
    summary="Submit risk feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_risk_feedback(
    request: SubmitRiskFeedbackRequest,
    capture_service: Any = Depends(get_feedback_capture),  # noqa: B008
) -> FeedbackResponse:
    try:
        record = await capture_service.capture_risk_feedback(
            assessment_id=request.assessment_id,
            rating=request.rating,
            corrected_risk_score=request.corrected_score,
            comment=request.comment,
        )

        return FeedbackResponse(
            record_id=record.record_id,
            status=record.status,
            message="Risk feedback captured successfully",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Risk feedback submission failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk feedback submission failed",
        ) from exc


@router.post(
    "/forecast",
    response_model=FeedbackResponse,
    summary="Submit forecast feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_forecast_feedback(
    request: SubmitForecastFeedbackRequest,
    capture_service: Any = Depends(get_feedback_capture),  # noqa: B008
) -> FeedbackResponse:
    try:
        record = await capture_service.capture_forecast_feedback(
            forecast_id=request.forecast_id,
            rating=request.rating,
            observed_values=request.observed_values,
            comment=request.comment,
        )

        return FeedbackResponse(
            record_id=record.record_id,
            status=record.status,
            message="Forecast feedback captured successfully",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Forecast feedback submission failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast feedback submission failed",
        ) from exc


@router.post(
    "/general",
    response_model=FeedbackResponse,
    summary="Submit general feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_general_feedback(
    request: SubmitGeneralFeedbackRequest,
    capture_service: Any = Depends(get_feedback_capture),  # noqa: B008
) -> FeedbackResponse:
    try:
        record = await capture_service.capture_general_feedback(
            location_id=request.location_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comment=request.comment,
        )

        return FeedbackResponse(
            record_id=record.record_id,
            status=record.status,
            message="General feedback captured successfully",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("General feedback submission failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="General feedback submission failed",
        ) from exc


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    summary="Get feedback statistics",
)
async def get_feedback_stats(
    analyzer: Any = Depends(get_feedback_analyzer),  # noqa: B008
) -> FeedbackStatsResponse:
    try:
        stats = await analyzer.get_overview_stats()

        return FeedbackStatsResponse(
            total_feedback=stats.get("total_feedback", 0),
            avg_rating=stats.get("avg_rating", 0.0),
            rating_std=stats.get("rating_std", 0.0),
            rating_distribution=stats.get("rating_counts", {}),
            feedback_types=stats.get("feedback_types", {}),
        )
    except Exception as exc:
        _logger.exception("Feedback stats retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback statistics retrieval failed",
        ) from exc


@router.get(
    "/entries",
    summary="List feedback entries for dashboard analytics",
)
async def list_feedback_entries(
    analyzer: Any = Depends(get_feedback_analyzer),  # noqa: B008
) -> dict[str, Any]:
    try:
        entries = []
        if hasattr(analyzer, "list_dashboard_rows"):
            entries = analyzer.list_dashboard_rows()
        return {"entries": entries, "total": len(entries)}
    except Exception as exc:
        _logger.exception("Feedback entries retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback entries retrieval failed",
        ) from exc


@router.get(
    "/trend",
    response_model=FeedbackTrendResponse,
    summary="Get feedback trend",
)
async def get_feedback_trend(
    days: int = 90,
    analyzer: Any = Depends(get_feedback_analyzer),  # noqa: B008
) -> FeedbackTrendResponse:
    try:
        trend = await analyzer.get_improvement_trend(days=days)

        return FeedbackTrendResponse(
            overall_trend=trend.get("overall_trend", 0.0),
            first_period_avg=trend.get("first_period_avg", 0.0),
            second_period_avg=trend.get("second_period_avg", 0.0),
            trend_direction=trend.get("trend_direction", "insufficient_data"),
            improvement_pct=trend.get("improvement_pct", 0.0),
        )
    except Exception as exc:
        _logger.exception("Feedback trend retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback trend retrieval failed",
        ) from exc


@router.get(
    "/location/{location_id}",
    response_model=LocationFeedbackResponse,
    summary="Get location feedback performance",
)
async def get_location_feedback(
    location_id: str,
    analyzer: Any = Depends(get_feedback_analyzer),  # noqa: B008
) -> LocationFeedbackResponse:
    try:
        performance = await analyzer.get_location_performance(
            location_id=location_id,
        )

        return LocationFeedbackResponse(
            location_id=location_id,
            total_feedback=performance.get("total_feedback", 0),
            avg_rating=performance.get("avg_rating", 0.0),
            trend=performance.get("trend", "insufficient_data"),
            recent_avg=performance.get("recent_avg"),
        )
    except Exception as exc:
        _logger.exception("Location feedback retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Location feedback retrieval failed",
        ) from exc
