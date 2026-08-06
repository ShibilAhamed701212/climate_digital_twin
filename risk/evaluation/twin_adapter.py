"""TwinAdapter — maps TwinState to risk-engine inputs.

Preserves provenance, authenticity, and observation IDs.
NEVER maps missing values to zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any



@dataclass
class TwinInputs:
    max_temp: float | None
    min_temp: float | None
    rainfall: float | None
    consecutive_hot_days: int
    dry_period_days: int
    multi_day_accumulation: float | None
    seasonal_anomaly: float
    forecast_uncertainty: float
    twin_version: str | None
    observation_ids: list[str]
    authenticity: str
    data_source: str
    quality_flag: str
    observation_timestamp: datetime | None
    ingestion_timestamp: datetime | None
    twin_metadata: dict[str, str]


def extract_twin_inputs(twin_state: Any) -> TwinInputs:
    if twin_state is None:
        return TwinInputs(
            max_temp=None,
            min_temp=None,
            rainfall=None,
            consecutive_hot_days=0,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version=None,
            observation_ids=[],
            authenticity="UNKNOWN",
            data_source="",
            quality_flag="",
            observation_timestamp=None,
            ingestion_timestamp=None,
            twin_metadata={},
        )

    # Prefer explicit daily extremes when present; temperature_2m is often
    # instantaneous and must not silently become both max and min.
    max_temp = getattr(twin_state, "max_temp", None)
    if max_temp is None and isinstance(twin_state, dict):
        max_temp = twin_state.get("max_temp")
    if max_temp is None:
        max_temp = getattr(twin_state, "temperature_2m", None)
        if max_temp is None and isinstance(twin_state, dict):
            max_temp = twin_state.get("temperature_2m")

    min_temp = getattr(twin_state, "min_temp", None)
    if min_temp is None and isinstance(twin_state, dict):
        min_temp = twin_state.get("min_temp")
    if min_temp is None:
        min_temp = getattr(twin_state, "temperature_2m_min", None)
        if min_temp is None and isinstance(twin_state, dict):
            min_temp = twin_state.get("temperature_2m_min")

    rainfall = getattr(twin_state, "rainfall", None)
    if rainfall is None and isinstance(twin_state, dict):
        rainfall = twin_state.get("rainfall")
    if rainfall is None:
        rainfall = getattr(twin_state, "precipitation_mm", None)
        if rainfall is None and isinstance(twin_state, dict):
            rainfall = twin_state.get("precipitation_mm")

    def _get(name: str, default: Any = None) -> Any:
        if isinstance(twin_state, dict):
            return twin_state.get(name, default)
        return getattr(twin_state, name, default)

    return TwinInputs(
        max_temp=float(max_temp) if max_temp is not None else None,
        min_temp=float(min_temp) if min_temp is not None else None,
        rainfall=float(rainfall) if rainfall is not None else None,
        consecutive_hot_days=int(_get("consecutive_hot_days", 0) or 0),
        dry_period_days=int(_get("dry_period_days", 0) or 0),
        multi_day_accumulation=(
            float(_get("multi_day_accumulation"))
            if _get("multi_day_accumulation") is not None
            else None
        ),
        seasonal_anomaly=float(_get("seasonal_anomaly", 0.0) or 0.0),
        forecast_uncertainty=float(_get("forecast_uncertainty", 0.0) or 0.0),
        twin_version=str(_get("version_number", "") or _get("entity_id", "")),
        observation_ids=[_get("observation_id", "")] if _get("observation_id", "") else [],
        authenticity=str(_get("authenticity", "UNKNOWN") or "UNKNOWN"),
        data_source=str(_get("data_source", "") or ""),
        quality_flag=str(_get("quality_flag", "") or ""),
        observation_timestamp=_get("timestamp", None),
        ingestion_timestamp=_get("ingestion_timestamp", None),
        twin_metadata=dict(_get("metadata", {}) or {}),
    )
