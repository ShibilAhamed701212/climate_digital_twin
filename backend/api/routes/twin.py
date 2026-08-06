from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_twin_manager
from backend.api.models import (
    RollbackRequest,
    RollbackResponse,
    TwinEntityResponse,
    TwinHistoryResponse,
    TwinStateResponse,
    UpdateTwinStateRequest,
    UpdateTwinStateResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twin", tags=["Digital Twin"])


@router.get(
    "/state/{entity_id}",
    response_model=TwinStateResponse,
    summary="Get twin state",
)
async def get_twin_state(
    entity_id: str,
    twin_manager: Any = Depends(get_twin_manager),  # noqa: B008
) -> TwinStateResponse:
    try:
        state = await twin_manager.get_current_state(entity_id)

        return TwinStateResponse(
            entity_id=state.entity_id,
            timestamp=state.timestamp.isoformat(),
            temperature_2m=state.temperature_2m,
            precipitation_mm=state.precipitation_mm,
            humidity_pct=state.humidity_pct,
            pressure_hpa=state.pressure_hpa,
            wind_speed_10m=state.wind_speed_10m,
            data_source=state.data_source,
            quality_flag=state.quality_flag,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Twin state retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twin state retrieval failed",
        ) from exc


@router.post(
    "/state",
    response_model=UpdateTwinStateResponse,
    summary="Update twin state",
    status_code=status.HTTP_201_CREATED,
)
async def update_twin_state(
    request: UpdateTwinStateRequest,
    twin_manager: Any = Depends(get_twin_manager),  # noqa: B008
) -> UpdateTwinStateResponse:
    try:
        from simulator.models.twin_state import StateDelta

        delta = StateDelta(
            entity_id=request.entity_id,
            from_version_id="",
            to_version_id="",
            delta_temperature=request.delta_temperature,
            delta_precipitation=request.delta_precipitation,
            delta_humidity=request.delta_humidity,
            delta_pressure=request.delta_pressure,
            delta_wind_speed=request.delta_wind_speed,
        )

        version = await twin_manager.update_state(
            location_id=request.entity_id,
            delta=delta,
            source=request.source,
        )

        return UpdateTwinStateResponse(
            version_id=version.version_id,
            version_number=version.version_number,
            entity_id=request.entity_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Twin state update failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twin state update failed",
        ) from exc


@router.get(
    "/entity/{entity_id}",
    response_model=TwinEntityResponse,
    summary="Get entity details",
)
async def get_entity(
    entity_id: str,
    twin_manager: Any = Depends(get_twin_manager),  # noqa: B008
) -> TwinEntityResponse:
    try:
        state = await twin_manager.get_current_state(entity_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        return TwinEntityResponse(
            entity_id=entity_id,
            name=state.get("name", entity_id),
            location_id=state.get("location_id", entity_id),
            latitude=state.get("latitude", 0.0),
            longitude=state.get("longitude", 0.0),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Entity retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entity retrieval failed",
        ) from exc


@router.get(
    "/history/{entity_id}",
    response_model=TwinHistoryResponse,
    summary="Get state history",
)
async def get_state_history(
    entity_id: str,
    twin_manager: Any = Depends(get_twin_manager),  # noqa: B008
) -> TwinHistoryResponse:
    try:
        history = await twin_manager.get_version_history(entity_id)

        version_list: list[dict[str, Any]] = []
        for v in history:
            version_list.append(
                {
                    "version_id": v.version_id,
                    "version_number": v.version_number,
                    "created_at": v.created_at.isoformat(),
                    "created_by": v.created_by,
                    "description": v.description,
                    "state": _version_state_dict(v.state),
                }
            )

        return TwinHistoryResponse(
            entity_id=entity_id,
            versions=version_list,
            total_versions=len(version_list),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Version history retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Version history retrieval failed",
        ) from exc


def _version_state_dict(state: Any) -> dict[str, Any] | None:
    """Extract the weather snapshot stored in a twin state version, if any."""
    if state is None:
        return None
    temperature = getattr(state, "temperature_2m", None)
    if temperature is None:
        return None
    ts = getattr(state, "timestamp", None)
    timestamp = ts.isoformat() if isinstance(ts, datetime) else ""
    return {
        "timestamp": timestamp,
        "temperature_2m": float(temperature),
        "precipitation_mm": float(getattr(state, "precipitation_mm", 0.0) or 0.0),
        "humidity_pct": float(getattr(state, "humidity_pct", 0.0) or 0.0),
        "pressure_hpa": float(getattr(state, "pressure_hpa", 0.0) or 0.0),
        "wind_speed_10m": float(getattr(state, "wind_speed_10m", 0.0) or 0.0),
        "data_source": getattr(state, "data_source", ""),
        "quality_flag": getattr(state, "quality_flag", ""),
    }


@router.post(
    "/rollback",
    response_model=RollbackResponse,
    summary="Rollback to version",
)
async def rollback_state(
    request: RollbackRequest,
    twin_manager: Any = Depends(get_twin_manager),  # noqa: B008
) -> RollbackResponse:
    try:
        await twin_manager.rollback(
            location_id=request.entity_id,
            version_number=request.version_number,
        )

        return RollbackResponse(
            entity_id=request.entity_id,
            rolled_back_to_version=request.version_number,
            new_version_number=0,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("State rollback failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="State rollback failed",
        ) from exc
