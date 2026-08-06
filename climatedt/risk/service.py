"""Risk Service — Phase 4: wires REAL Twin state + forecast data into the
HazardEvaluator.  No hardcoded zeros.  No fake SHAP.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from risk.evaluation.hazard_evaluator import HazardEvaluator
from risk.evaluation.twin_adapter import TwinInputs, extract_twin_inputs
from risk.evaluation.forecast_adapter import extract_forecast_inputs
from risk.evaluation.quality_gate import severity_from_score
from risk.models.hazard import HazardAssessment

logger = logging.getLogger(__name__)


class _Assessment:
    """Adapter from HazardAssessment to the existing _Assessment shape
    so the backend API routes continue to work with minimal changes."""

    def __init__(
        self, ha: HazardAssessment, all_hazards: list[HazardAssessment] | None = None
    ) -> None:
        self._ha = ha
        self.assessment_id = ha.assessment_id
        self.location_id = ha.location_id
        self.composite_score = ha.hazard_score / 100.0
        self.composite_category = ha.severity.value
        self.timestamp = datetime.now(UTC)
        self.metadata = {
            "hazard_type": ha.hazard_type,
            "assessment_type": ha.assessment_type.value,
            "assessment_confidence": str(ha.assessment_confidence),
            "data_quality": ha.data_quality.value,
            "data_freshness": ha.data_freshness.value,
            "severity": ha.severity.value,
            "method": ha.method,
            "config_version": ha.config_version,
        }

        class _Score:
            def __init__(self, ha_: HazardAssessment) -> None:
                self.hazard_type = ha_.hazard_type
                self.score = ha_.hazard_score / 100.0
                self.category = ha_.severity.value
                self.description = (
                    f"{ha_.hazard_type} hazard: severity={ha_.severity.value}, "
                    f"confidence={ha_.assessment_confidence:.2f}"
                )

        # Expose every assessed hazard, not just the primary, so the
        # dashboard ranking table gets real heat/flood/drought columns.
        hazards = all_hazards if all_hazards else [ha]
        self.scores = [_Score(h) for h in hazards]

    def to_dict(self) -> dict[str, Any]:
        ha = self._ha
        evidence_list = [
            {
                "factor": e.factor,
                "value": e.value,
                "unit": e.unit,
                "threshold": e.threshold,
                "effect": e.effect,
            }
            for e in ha.evidence
        ]
        return {
            "assessment_id": ha.assessment_id,
            "location_id": ha.location_id,
            "hazard_type": ha.hazard_type,
            "assessment_type": ha.assessment_type.value,
            "severity": ha.severity.value,
            "hazard_score": ha.hazard_score,
            "assessment_confidence": ha.assessment_confidence,
            "data_quality": ha.data_quality.value,
            "data_freshness": ha.data_freshness.value,
            "method": ha.method,
            "method_version": ha.method_version,
            "config_version": ha.config_version,
            "evidence": evidence_list,
            "thresholds_triggered": ha.thresholds_triggered,
            "source_twin_version": ha.source_twin_version,
            "source_observation_ids": ha.source_observation_ids,
            "source_forecast_ids": ha.source_forecast_ids,
            "provenance": ha.provenance,
            "historical_context": ha.historical_context.to_dict()
            if ha.historical_context
            else None,
            "attribution": {
                "primary_driver": ha.attribution.primary_driver,
                "factors": [
                    {"factor": f.factor, "value": f.value, "unit": f.unit, "effect": f.effect}
                    for f in ha.attribution.factors
                ],
            }
            if ha.attribution
            else None,
            "generated_at": ha.generated_at,
            "alerts": [],
        }


class RiskService:
    """Phase 4 RiskService — consumes REAL Twin state + forecasts.
    NO hardcoded zeros.  NO fake SHAP.  Full provenance.
    """

    def __init__(
        self,
        evaluator: HazardEvaluator | None = None,
    ) -> None:
        self._evaluator = evaluator or HazardEvaluator()
        self._hazard_store = self._evaluator.hazard_store
        self._alert_store = self._evaluator.alert_store
        self._explainer = _Explainer()

    async def assess_location(
        self,
        location_id: str,
        _latitude: float = 0.0,
        _longitude: float = 0.0,
        _include_explainability: bool = False,
    ) -> _Assessment:
        twin_state = await self._get_twin_state(location_id)
        twin_inputs = extract_twin_inputs(twin_state)
        twin_inputs = await self._enrich_twin_inputs(
            location_id=location_id,
            twin_inputs=twin_inputs,
            latitude=_latitude,
            longitude=_longitude,
        )

        # #region agent log
        try:
            import json as _json
            import time as _time
            from pathlib import Path as _Path

            _p = _Path("debug-fb7a7b.log")
            with _p.open("a", encoding="utf-8") as _f:
                _f.write(
                    _json.dumps(
                        {
                            "sessionId": "fb7a7b",
                            "hypothesisId": "A",
                            "location": "RiskService.assess_location",
                            "message": "enriched twin inputs",
                            "data": {
                                "location_id": location_id,
                                "max_temp": twin_inputs.max_temp,
                                "min_temp": twin_inputs.min_temp,
                                "rainfall": twin_inputs.rainfall,
                                "dry_period_days": twin_inputs.dry_period_days,
                                "consecutive_hot_days": twin_inputs.consecutive_hot_days,
                                "multi_day_accumulation": twin_inputs.multi_day_accumulation,
                                "seasonal_anomaly": twin_inputs.seasonal_anomaly,
                                "data_source": twin_inputs.data_source,
                                "authenticity": twin_inputs.authenticity,
                            },
                            "timestamp": int(_time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion

        assessments, _ = self._evaluator.process_and_store(
            twin_inputs=twin_inputs,
            forecast_inputs=None,
            location_id=location_id,
        )
        if not assessments or all(a.hazard_type == "unknown" for a in assessments):
            return self._empty_assessment(location_id)
        primary = max(assessments, key=lambda a: a.hazard_score)
        result = _Assessment(primary, all_hazards=assessments)

        # Composite = weighted blend of hazards (not just the primary dryness score).
        from risk.scoring.composite_risk import calculate_composite_risk

        by_type = {a.hazard_type: float(a.hazard_score) for a in assessments}
        composite = calculate_composite_risk(
            heat_score=by_type.get("heat", 0.0),
            flood_score=by_type.get("heavy_rain", by_type.get("flood", 0.0)),
            drought_score=by_type.get("dryness", by_type.get("drought", 0.0)),
        )
        result.composite_score = composite.score / 100.0
        result.composite_category = severity_from_score(composite.score).value
        # RiskAssessResponse.metadata is Dict[str, str] — keep values serializable strings.
        result.metadata = {
            **{k: str(v) for k, v in (result.metadata or {}).items()},
            "composite_method": "WEIGHTED_HEAT_FLOOD_DRYNESS",
            "composite_weights": json.dumps(composite.weights),
            "primary_hazard": str(primary.hazard_type),
            "input_max_temp": "" if twin_inputs.max_temp is None else str(twin_inputs.max_temp),
            "input_min_temp": "" if twin_inputs.min_temp is None else str(twin_inputs.min_temp),
            "input_rainfall": "" if twin_inputs.rainfall is None else str(twin_inputs.rainfall),
            "input_dry_period_days": str(twin_inputs.dry_period_days),
            "input_consecutive_hot_days": str(twin_inputs.consecutive_hot_days),
            "input_multi_day_accumulation": ""
            if twin_inputs.multi_day_accumulation is None
            else str(twin_inputs.multi_day_accumulation),
            "input_seasonal_anomaly": str(twin_inputs.seasonal_anomaly),
            "input_data_source": str(twin_inputs.data_source),
        }
        return result

    async def _enrich_twin_inputs(
        self,
        location_id: str,
        twin_inputs: TwinInputs,
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> TwinInputs:
        """Fill daily extremes + spell/accumulation features from REAL history."""
        from dataclasses import replace

        from risk.evaluation.feature_enrichment import (
            climatology_from_real_csv,
            derive_series_features,
        )

        rains: list[float] = []
        temps: list[float] = []
        try:
            from climatedt.twin.state_manager import TwinStateManager

            mgr = TwinStateManager()
            history = await mgr.get_version_history(location_id)
            for version in reversed(list(history or [])[-30:]):
                state = getattr(version, "state", None) or getattr(version, "entity_state", None)
                if state is None:
                    state = version
                rain = getattr(state, "precipitation_mm", None)
                if rain is None:
                    rain = getattr(state, "rainfall", None)
                temp = getattr(state, "max_temp", None)
                if temp is None:
                    temp = getattr(state, "temperature_2m", None)
                if rain is not None:
                    rains.append(float(rain))
                if temp is not None:
                    temps.append(float(temp))
        except Exception as exc:
            logger.debug("Twin history enrichment failed for %s: %s", location_id, exc)

        if twin_inputs.rainfall is not None and (not rains or rains[-1] != twin_inputs.rainfall):
            rains.append(float(twin_inputs.rainfall))
        if twin_inputs.max_temp is not None and (not temps or temps[-1] != twin_inputs.max_temp):
            temps.append(float(twin_inputs.max_temp))

        features = derive_series_features(rains, temps)
        csv_climo = climatology_from_real_csv(
            latitude if latitude else None,
            longitude if longitude else None,
        )

        # Prefer Open-Meteo daily max/min when twin only has instantaneous temp.
        max_temp = twin_inputs.max_temp
        min_temp = twin_inputs.min_temp
        try:
            import httpx

            if latitude and longitude:
                resp = httpx.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",
                        "forecast_days": 1,
                    },
                    timeout=8.0,
                )
                if resp.status_code == 200:
                    daily = resp.json().get("daily", {})
                    dmax = (daily.get("temperature_2m_max") or [None])[0]
                    dmin = (daily.get("temperature_2m_min") or [None])[0]
                    drain = (daily.get("precipitation_sum") or [None])[0]
                    if dmax is not None:
                        max_temp = float(dmax)
                    if dmin is not None:
                        min_temp = float(dmin)
                    if drain is not None and twin_inputs.rainfall is None:
                        twin_inputs = replace(twin_inputs, rainfall=float(drain))
        except Exception as exc:
            logger.debug("Open-Meteo daily enrich failed for %s: %s", location_id, exc)

        seasonal_anomaly = float(features.get("seasonal_anomaly", 0.0) or 0.0)
        mean_temp = csv_climo.get("mean_max_temp") or features.get("mean_max_temp")
        if max_temp is not None and mean_temp:
            seasonal_anomaly = float(max_temp) - float(mean_temp)

        meta = dict(twin_inputs.twin_metadata or {})
        meta.update(
            {
                "latitude": str(latitude or meta.get("latitude", "")),
                "longitude": str(longitude or meta.get("longitude", "")),
                "climatology_source": "real_csv+twin_history"
                if csv_climo
                else "twin_history_or_default",
                "csv_mean_rainfall": str(csv_climo.get("mean_rainfall", "")),
                "csv_mean_max_temp": str(csv_climo.get("mean_max_temp", "")),
            }
        )

        authenticity = twin_inputs.authenticity
        if authenticity in {"", "UNKNOWN"} and twin_inputs.data_source == "open_meteo":
            authenticity = "REAL"

        return replace(
            twin_inputs,
            max_temp=max_temp,
            min_temp=min_temp,
            consecutive_hot_days=int(
                twin_inputs.consecutive_hot_days or features.get("consecutive_hot_days", 0) or 0
            ),
            dry_period_days=int(
                twin_inputs.dry_period_days or features.get("dry_period_days", 0) or 0
            ),
            multi_day_accumulation=(
                twin_inputs.multi_day_accumulation
                if twin_inputs.multi_day_accumulation is not None
                else float(features.get("multi_day_accumulation", 0.0) or 0.0)
            ),
            seasonal_anomaly=seasonal_anomaly,
            authenticity=authenticity,
            twin_metadata=meta,
        )

    async def _get_twin_state(self, location_id: str) -> Any:
        try:
            from climatedt.twin.state_manager import TwinStateManager

            mgr = TwinStateManager()
            return await mgr.get_current_state(location_id)
        except ImportError:
            logger.warning("TwinStateManager not available")
        except ValueError:
            logger.info("No twin state found for %s", location_id)
        except Exception as exc:
            logger.warning("Failed to get twin state for %s: %s", location_id, exc)
        return None

    async def assess_batch(
        self,
        location_ids: list[str],
        latitudes: list[float] | None = None,
        longitudes: list[float] | None = None,
    ) -> dict[str, _Assessment]:
        results: dict[str, _Assessment] = {}
        for loc_id in location_ids:
            results[loc_id] = await self.assess_location(loc_id)
        return results

    async def get_risk_trend(
        self,
        location_id: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
        _observations: list[Any] | None = None,
        _days: int = 90,
    ) -> list[_Assessment]:
        history = self._hazard_store.list_by_location(location_id, limit=_days)
        if not history:
            return [await self.assess_location(location_id)]
        return [_Assessment(h) for h in history]

    async def assess_forecast(
        self,
        location_id: str,
        forecast_id: str | None = None,
    ) -> _Assessment | None:
        forecast = await self._get_forecast(location_id, forecast_id)
        if forecast is None:
            logger.info("No forecast found for %s", location_id)
            return None

        forecast_inputs = extract_forecast_inputs(forecast)
        assessments, _ = self._evaluator.process_and_store(
            twin_inputs=None,
            forecast_inputs=forecast_inputs,
            location_id=location_id,
        )
        if not assessments or all(a.hazard_type == "unknown" for a in assessments):
            return None
        primary = max(assessments, key=lambda a: a.hazard_score)
        return _Assessment(primary)

    async def _get_forecast(self, location_id: str, forecast_id: str | None = None) -> Any:
        try:
            from models.forecast_provenance import ForecastStore

            store = ForecastStore()
            recent = store.list_recent(limit=5)
            for f in recent:
                if f.location_id == location_id:
                    if forecast_id is None or f.forecast_id == forecast_id:
                        return f
        except Exception as exc:
            logger.warning("Failed to get forecast for %s: %s", location_id, exc)
        return None

    def get_active_alerts(self, location_id: str) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._alert_store.list_active_by_location(location_id)]

    def get_supported_hazards(self) -> dict[str, Any]:
        from risk.models.hazard import UNSUPPORTED_HAZARDS

        config_hazards = self._evaluator._config.get("hazards", {})
        supported = {}
        unsupported = {}
        for name, cfg in config_hazards.items():
            if name in UNSUPPORTED_HAZARDS or not cfg.get("enabled", False):
                unsupported[name] = {"reason": cfg.get("reason", "Not implemented")}
            else:
                supported[name] = {
                    "semantics": cfg.get("operational_semantics", ""),
                    "method": cfg.get("method", ""),
                }
        return {"supported": supported, "unsupported": unsupported}

    def _empty_assessment(self, location_id: str) -> _Assessment:
        from risk.models.hazard import Severity, DataQuality, Freshness

        dummy = HazardAssessment(
            location_id=location_id,
            severity=Severity.NONE,
            data_quality=DataQuality.REJECTED,
            data_freshness=Freshness.UNAVAILABLE,
            method="NONE",
            config_version="2026-07-30",
        )
        return _Assessment(dummy)


class _Explainer:
    def factor_contribution(self, assessment: Any) -> dict[str, float]:
        """Deterministic factor contribution from the assessment's attribution."""
        ha = getattr(assessment, "_ha", None)
        if ha is None or ha.attribution is None:
            return {}
        return {f.factor: f.value for f in ha.attribution.factors}
