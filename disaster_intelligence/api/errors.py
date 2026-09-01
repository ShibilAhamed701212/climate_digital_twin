from __future__ import annotations

from datetime import UTC, datetime

from fastapi.responses import JSONResponse

from disaster_intelligence.domain.errors import DisasterError


def error_response(status: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "detail": detail,
            "error_code": code,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )


def from_disaster_error(exc: DisasterError) -> JSONResponse:
    mapping = {
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "JOB_BUSY": 409,
        "PAYLOAD_TOO_LARGE": 413,
        "UNSUPPORTED_MEDIA": 415,
        "INVALID_GEOTIFF": 400,
        "TASK_NOT_ENABLED": 501,
        "STAC_ERROR": 502,
        "AOI_OUTSIDE_REGION": 400,
        "JOB_FAILED": 500,
        "INTERNAL_ERROR": 500,
    }
    return error_response(mapping.get(exc.code, 500), exc.message, exc.code)
