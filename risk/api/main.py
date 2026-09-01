"""Risk Engine API — exposes climate risk assessment via REST.

Endpoints:
  GET  /health              — health check
  POST /risk/assess         — assess all risk types for a location
  POST /risk/heat           — assess heat risk only
  POST /risk/heavy-rain     — assess heavy-rain hazard only
  POST /risk/dryness        — assess dryness hazard only
  POST /risk/composite      — assess composite risk only
  POST /risk/report         — generate and save a full risk report
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from risk.engine.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

_engine: RiskEngine | None = None


class RiskAssessRequest(BaseModel):
    location_id: str
    district: str = ""
    max_temp: float = Field(default=30.0, description="Maximum temperature in Celsius")
    min_temp: float = Field(default=20.0, description="Minimum temperature in Celsius")
    rainfall: float = Field(default=0.0, description="Current rainfall in mm")
    historical_mean_rainfall: float = Field(default=100.0, description="Long-term average rainfall")
    historical_mean_temp: float = Field(
        default=28.0, description="Long-term average max temperature"
    )
    consecutive_hot_days: int = 0
    dry_period_days: int = 0
    multi_day_accumulation: float | None = None
    seasonal_anomaly: float = 0.0
    forecast_uncertainty: float = 0.0
    prediction_confidence: float = 0.0
    agriculture_features: dict[str, float | str] | None = None


class RiskReportRequest(RiskAssessRequest):
    formats: list[str] | None = Field(None, description="Output formats (json, markdown)")


class SimpleRiskRequest(BaseModel):
    score: float = Field(default=0.0, ge=0, le=100)
    heat_score: float | None = Field(None, ge=0, le=100)
    heavy_rain_score: float | None = Field(None, ge=0, le=100)
    dryness_score: float | None = Field(None, ge=0, le=100)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _engine
    _engine = RiskEngine()
    logger.info("RiskEngine initialized")
    yield
    _engine = None


app = FastAPI(title="Risk Engine API", version="2.1.0", lifespan=lifespan)


def _get_engine() -> RiskEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


@app.get("/health")
def health():
    return {"status": "healthy", "service": "risk-engine", "version": "2.1.0"}


@app.post("/risk/assess")
def assess_risk(req: RiskAssessRequest) -> dict[str, Any]:
    eng = _get_engine()
    report = eng.assess_all(
        location_id=req.location_id,
        district=req.district,
        max_temp=req.max_temp,
        min_temp=req.min_temp,
        rainfall=req.rainfall,
        historical_mean_rainfall=req.historical_mean_rainfall,
        historical_mean_temp=req.historical_mean_temp,
        consecutive_hot_days=req.consecutive_hot_days,
        dry_period_days=req.dry_period_days,
        multi_day_accumulation=req.multi_day_accumulation,
        seasonal_anomaly=req.seasonal_anomaly,
        forecast_uncertainty=req.forecast_uncertainty,
        prediction_confidence=req.prediction_confidence,
        agriculture_features=req.agriculture_features,
    )
    return report.to_dict()


@app.post("/risk/heat")
def assess_heat(req: RiskAssessRequest) -> dict[str, Any]:
    eng = _get_engine()
    heat = eng.assess_heat_risk(
        max_temp=req.max_temp,
        consecutive_hot_days=req.consecutive_hot_days,
        seasonal_anomaly=req.seasonal_anomaly,
    )
    return heat.__dict__


@app.post("/risk/heavy_rain")
def assess_heavy_rain(req: RiskAssessRequest) -> dict[str, Any]:
    eng = _get_engine()
    heavy_rain = eng.assess_flood_risk(
        rainfall=req.rainfall,
        multi_day_accumulation=req.multi_day_accumulation,
        forecast_uncertainty=req.forecast_uncertainty,
    )
    return heavy_rain.__dict__


@app.post("/risk/flood", deprecated=True)
def assess_flood_deprecated(req: RiskAssessRequest) -> dict[str, Any]:
    """Deprecated — use /risk/heavy_rain instead."""
    return assess_heavy_rain(req)


@app.post("/risk/dryness")
def assess_dryness(req: RiskAssessRequest) -> dict[str, Any]:
    eng = _get_engine()
    dryness = eng.assess_drought_risk(
        rainfall=req.rainfall,
        historical_mean_rainfall=req.historical_mean_rainfall,
        max_temp=req.max_temp,
        historical_mean_temp=req.historical_mean_temp,
        dry_period_days=req.dry_period_days,
    )
    return dryness.__dict__


@app.post("/risk/drought", deprecated=True)
def assess_drought_deprecated(req: RiskAssessRequest) -> dict[str, Any]:
    """Deprecated — use /risk/dryness instead."""
    return assess_dryness(req)


@app.post("/risk/composite")
def assess_composite(req: SimpleRiskRequest) -> dict[str, Any]:
    eng = _get_engine()
    composite = eng.assess_composite_risk(
        heat_score=req.heat_score or req.score,
        flood_score=req.heavy_rain_score or req.score,
        drought_score=req.dryness_score or req.score,
    )
    return composite.__dict__


@app.post("/risk/report")
def generate_report(req: RiskReportRequest) -> dict[str, Any]:
    eng = _get_engine()
    report = eng.assess_all(
        location_id=req.location_id,
        district=req.district,
        max_temp=req.max_temp,
        min_temp=req.min_temp,
        rainfall=req.rainfall,
        historical_mean_rainfall=req.historical_mean_rainfall,
        historical_mean_temp=req.historical_mean_temp,
        consecutive_hot_days=req.consecutive_hot_days,
        dry_period_days=req.dry_period_days,
        multi_day_accumulation=req.multi_day_accumulation,
        seasonal_anomaly=req.seasonal_anomaly,
        forecast_uncertainty=req.forecast_uncertainty,
        prediction_confidence=req.prediction_confidence,
    )
    outputs = eng.generate_full_report(
        location_id=req.location_id,
        district=req.district,
        report=report,
        formats=req.formats,
    )
    return {"report": report.to_dict(), "outputs": outputs}
