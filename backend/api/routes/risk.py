from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_risk_service
from backend.api.models import (
    BatchRiskAssessRequest,
    BatchRiskAssessResponse,
    RiskAssessRequest,
    RiskAssessResponse,
    RiskExplainRequest,
    RiskExplainResponse,
    RiskTrendResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["Risk Assessment"])


def _assessment_to_response(assessment: Any) -> RiskAssessResponse:
    raw_score = getattr(assessment, "composite_score", 0.0)
    return RiskAssessResponse(
        assessment_id=getattr(assessment, "assessment_id", ""),
        location_id=getattr(assessment, "location_id", ""),
        composite_score=max(0.0, min(1.0, raw_score)),
        composite_category=getattr(assessment, "composite_category", "unknown"),
        scores=[
            {
                "hazard_type": getattr(s, "hazard_type", "unknown"),
                "score": max(0.0, min(1.0, getattr(s, "score", 0.0))),
                "category": getattr(s, "category", "unknown"),
                "description": getattr(s, "description", ""),
            }
            for s in getattr(assessment, "scores", [])
        ],
        timestamp=getattr(assessment, "timestamp", datetime.now(UTC)).isoformat(),
        metadata=getattr(assessment, "metadata", {}),
    )


@router.post(
    "/assess",
    response_model=RiskAssessResponse,
    summary="Assess climate risk for a location",
    status_code=status.HTTP_200_OK,
)
async def assess_risk(
    request: RiskAssessRequest,
    risk_service: Any = Depends(get_risk_service),  # noqa: B008
) -> RiskAssessResponse:
    try:
        assessment = await risk_service.assess_location(
            location_id=request.location_id,
            _latitude=request.latitude,
            _longitude=request.longitude,
            _include_explainability=request.include_explainability,
        )
        return _assessment_to_response(assessment)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Risk assessment failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk assessment failed",
        ) from exc


@router.post(
    "/assess/batch",
    response_model=BatchRiskAssessResponse,
    summary="Batch risk assessment",
    status_code=status.HTTP_200_OK,
)
async def assess_risk_batch(
    request: BatchRiskAssessRequest,
    risk_service: Any = Depends(get_risk_service),  # noqa: B008
) -> BatchRiskAssessResponse:
    try:
        location_ids = [loc["location_id"] for loc in request.locations]
        latitudes = [loc.get("latitude", 0.0) for loc in request.locations]
        longitudes = [loc.get("longitude", 0.0) for loc in request.locations]

        assessments = await risk_service.assess_batch(
            location_ids=location_ids,
            latitudes=latitudes,
            longitudes=longitudes,
        )

        response_assessments: dict[str, RiskAssessResponse] = {}
        for loc_id, assessment in assessments.items():
            response_assessments[loc_id] = _assessment_to_response(assessment)

        return BatchRiskAssessResponse(
            assessments=response_assessments,
            total_locations=len(response_assessments),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Batch risk assessment failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch risk assessment failed",
        ) from exc


@router.get(
    "/trend/{location_id}",
    response_model=RiskTrendResponse,
    summary="Get risk trend for a location",
)
async def get_risk_trend(
    location_id: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    days: int = 90,
    risk_service: Any = Depends(get_risk_service),  # noqa: B008
) -> RiskTrendResponse:
    try:
        assessments = await risk_service.get_risk_trend(
            location_id=location_id,
            latitude=latitude,
            longitude=longitude,
            observations=[],
            days=days,
        )
        return RiskTrendResponse(
            location_id=location_id,
            assessments=[_assessment_to_response(a) for a in assessments],
            days_analysed=days,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Risk trend retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk trend retrieval failed",
        ) from exc


@router.post(
    "/explain",
    response_model=RiskExplainResponse,
    summary="Explain a risk assessment",
)
async def explain_risk(
    request: RiskExplainRequest,
    risk_service: Any = Depends(get_risk_service),  # noqa: B008
) -> RiskExplainResponse:
    try:
        explainer = getattr(risk_service, "_explainer", None)
        if explainer is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Explainer not available",
            )
        location_id = request.location_id or request.assessment_id
        assessment = await risk_service.assess_location(
            location_id=location_id,
            _latitude=request.latitude,
            _longitude=request.longitude,
        )

        contributions = explainer.factor_contribution(assessment)

        hazard_contributions: dict[str, dict[str, float]] = {}
        for factor, contrib in contributions.items():
            hazard_type = "composite"
            if hazard_type not in hazard_contributions:
                hazard_contributions[hazard_type] = {}
            hazard_contributions[hazard_type][factor] = contrib

        top_factors = sorted(
            contributions.keys(),
            key=lambda k: abs(contributions[k]),
            reverse=True,
        )[:5]

        return RiskExplainResponse(
            assessment_id=request.assessment_id,
            hazard_contributions=hazard_contributions,
            top_factors=top_factors,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Risk explanation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk explanation failed",
        ) from exc
