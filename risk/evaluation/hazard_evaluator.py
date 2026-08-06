"""HazardEvaluator — the Phase 4 hazard assessment orchestrator.

Quality gates, freshness checks, historical context, scoring via
existing risk engine, deterministic attribution, alert policy.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import yaml
from pathlib import Path

from risk.engine.risk_engine import RiskEngine
from risk.models.hazard import (
    AssessmentType,
    DataQuality,
    Freshness,
    HazardAssessment,
    HazardType,
    Severity,
)
from risk.evaluation.historical_context import HistoricalContextService
from risk.evaluation.quality_gate import (
    QualityGateConfig,
    check_freshness,
    check_quality,
    compute_confidence,
    severity_from_score,
)
from risk.evaluation.deterministic_attribution import (
    build_heat_attribution,
    build_heavy_rain_attribution,
    build_dryness_attribution,
)
from risk.evaluation.twin_adapter import TwinInputs
from risk.evaluation.forecast_adapter import ForecastInputs
from risk.evaluation.alert_policy import AlertPolicy
from risk.store.hazard_store import HazardStore
from risk.store.alert_store import AlertStore

logger = logging.getLogger(__name__)

CONFIG_VERSION = "2026-07-30"


class HazardEvaluator:
    """Assesses climate hazards from REAL Twin state or forecasts.

    Flow:  quality gate → freshness gate → historical context →
           existing risk scoring → evidence → attribution →
           severity → persistence → alert policy.
    """

    def __init__(
        self,
        risk_engine: RiskEngine | None = None,
        historical_context: HistoricalContextService | None = None,
        alert_policy: AlertPolicy | None = None,
        hazard_store: HazardStore | None = None,
        alert_store: AlertStore | None = None,
        config_path: str = "config/risk_config.yaml",
    ) -> None:
        self._engine = risk_engine or RiskEngine()
        self._historical = historical_context or HistoricalContextService()
        self._alert_policy = alert_policy or AlertPolicy(config_path)
        self._hazard_store = hazard_store or HazardStore()
        self._alert_store = alert_store or AlertStore()
        self._config = self._load_config(config_path)
        self._qc = QualityGateConfig.from_yaml_config(self._config)

    def _load_config(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            logger.warning("Risk config not found at %s — using defaults", path)
            return {}
        with open(p) as f:
            return yaml.safe_load(f) or {}

    # ── Observed hazard assessment ─────────────────────────────────────

    def assess_observed(self, twin_inputs: TwinInputs, location_id: str) -> list[HazardAssessment]:
        quality, reason = check_quality(
            twin_inputs.authenticity,
            twin_inputs.quality_flag,
            config=self._qc,
        )
        if quality == DataQuality.REJECTED:
            logger.info("Quality gate rejected %s: %s", location_id, reason)
            return [self._insufficient_data(location_id, reason, AssessmentType.OBSERVED)]

        freshness = check_freshness(twin_inputs.observation_timestamp, config=self._qc)
        if freshness == Freshness.UNAVAILABLE:
            return [
                self._insufficient_data(
                    location_id,
                    "no observation timestamp",
                    AssessmentType.OBSERVED,
                )
            ]

        return self._compute_assessments(
            location_id=location_id,
            assessment_type=AssessmentType.OBSERVED,
            twin_inputs=twin_inputs,
            forecast_inputs=None,
            quality=quality,
            freshness=freshness,
        )

    # ── Forecast hazard assessment ─────────────────────────────────────

    def assess_forecast(
        self, forecast_inputs: ForecastInputs, location_id: str
    ) -> list[HazardAssessment]:
        quality, reason = check_quality(
            forecast_inputs.authenticity,
            "validated",
            config=self._qc,
        )
        if quality == DataQuality.REJECTED:
            logger.info("Quality gate rejected forecast %s: %s", location_id, reason)
            return [self._insufficient_data(location_id, reason, AssessmentType.FORECAST)]

        freshness = Freshness.FRESH

        return self._compute_assessments(
            location_id=location_id,
            assessment_type=AssessmentType.FORECAST,
            twin_inputs=None,
            forecast_inputs=forecast_inputs,
            quality=quality,
            freshness=freshness,
        )

    # ── Historical backtest ────────────────────────────────────────────

    def assess_historical_backtest(
        self,
        location_id: str,
        max_temp: float | None,
        min_temp: float | None,
        rainfall: float | None,
        timestamp: datetime | str | None = None,
    ) -> list[HazardAssessment]:
        freshness = check_freshness(timestamp, config=self._qc)

        dummy_twin = TwinInputs(
            max_temp=max_temp,
            min_temp=min_temp,
            rainfall=rainfall,
            consecutive_hot_days=0,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="historical_backtest",
            observation_ids=[],
            authenticity="REAL",
            data_source="historical",
            quality_flag="validated",
            observation_timestamp=timestamp if isinstance(timestamp, datetime) else None,
            ingestion_timestamp=None,
            twin_metadata={},
        )

        return self._compute_assessments(
            location_id=location_id,
            assessment_type=AssessmentType.HISTORICAL_BACKTEST,
            twin_inputs=dummy_twin,
            forecast_inputs=None,
            quality=DataQuality.GOOD,
            freshness=freshness,
        )

    # ── Scenario (counterfactual) hazard assessment ──────────────────────

    def assess_scenario(self, twin_inputs: TwinInputs, location_id: str) -> list[HazardAssessment]:
        freshness = check_freshness(twin_inputs.observation_timestamp, config=self._qc)
        return self._compute_assessments(
            location_id=location_id,
            assessment_type=AssessmentType.SCENARIO,
            twin_inputs=twin_inputs,
            forecast_inputs=None,
            quality=DataQuality.GOOD,
            freshness=freshness,
        )

    # ── Internal computation ───────────────────────────────────────────

    def _compute_assessments(
        self,
        location_id: str,
        assessment_type: AssessmentType,
        twin_inputs: TwinInputs | None,
        forecast_inputs: ForecastInputs | None,
        quality: DataQuality,
        freshness: Freshness,
    ) -> list[HazardAssessment]:
        inputs = self._resolve_inputs(twin_inputs, forecast_inputs)
        if inputs is None:
            return [self._insufficient_data(location_id, "no usable inputs", assessment_type)]

        max_temp, min_temp, rainfall = inputs

        # Use REAL climatology when available. Defaulting rainfall baseline to
        # 100 mm/day made almost every Karnataka district collapse to dryness=40.
        rain_climo = self._historical.compute_climatology(location_id, "precipitation_mm")
        temp_climo = self._historical.compute_climatology(location_id, "temperature_2m")
        historical_mean_rainfall = rain_climo.get("mean")
        historical_mean_temp = temp_climo.get("mean")

        if historical_mean_rainfall is None and twin_inputs is not None:
            from risk.evaluation.feature_enrichment import climatology_from_real_csv

            lat = twin_inputs.twin_metadata.get("latitude")
            lon = twin_inputs.twin_metadata.get("longitude")
            try:
                lat_f = float(lat) if lat is not None else None
                lon_f = float(lon) if lon is not None else None
            except (TypeError, ValueError):
                lat_f = lon_f = None
            csv_climo = climatology_from_real_csv(lat_f, lon_f)
            historical_mean_rainfall = csv_climo.get("mean_rainfall")
            if historical_mean_temp is None:
                historical_mean_temp = csv_climo.get("mean_max_temp")

        # Karnataka typical daily rainfall ~3–5 mm; never use the old 100 mm default.
        if historical_mean_rainfall is None or historical_mean_rainfall <= 0:
            historical_mean_rainfall = 4.0
        if historical_mean_temp is None:
            historical_mean_temp = 28.0

        consecutive_hot_days = twin_inputs.consecutive_hot_days if twin_inputs else 0
        dry_period_days = twin_inputs.dry_period_days if twin_inputs else 0
        multi_day_accumulation = (
            twin_inputs.multi_day_accumulation if twin_inputs else None
        )
        seasonal_anomaly = twin_inputs.seasonal_anomaly if twin_inputs else 0.0
        if (
            seasonal_anomaly == 0.0
            and max_temp is not None
            and historical_mean_temp is not None
        ):
            seasonal_anomaly = float(max_temp) - float(historical_mean_temp)

        report = self._engine.assess_all(
            location_id=location_id,
            district=(twin_inputs.twin_metadata.get("district", "unknown") if twin_inputs else "unknown"),
            max_temp=max_temp if max_temp is not None else 0.0,
            min_temp=min_temp if min_temp is not None else 0.0,
            rainfall=rainfall if rainfall is not None else 0.0,
            historical_mean_rainfall=float(historical_mean_rainfall),
            historical_mean_temp=float(historical_mean_temp),
            consecutive_hot_days=int(consecutive_hot_days or 0),
            dry_period_days=int(dry_period_days or 0),
            multi_day_accumulation=multi_day_accumulation,
            seasonal_anomaly=float(seasonal_anomaly or 0.0),
        )

        assessments: list[HazardAssessment] = []

        # Heat hazard
        if report.heat_risk is not None and max_temp is not None:
            ctx = self._historical.get_historical_context(
                location_id,
                "temperature_2m",
                max_temp,
            )
            attr = build_heat_attribution(
                max_temp,
                twin_inputs.consecutive_hot_days if twin_inputs else 0,
                0.0,
                report.heat_risk.score,
            )
            score = report.heat_risk.score
            sev = severity_from_score(score, thresholds=self._qc)
            thresholds = []
            if max_temp > 35:
                thresholds.append("max_temp>35C")
            if twin_inputs and twin_inputs.consecutive_hot_days >= 3:
                thresholds.append("consecutive_hot_days>=3")
            assessments.append(
                self._build_assessment(
                    location_id=location_id,
                    assessment_type=assessment_type,
                    hazard_type=HazardType.HEAT,
                    score=score,
                    severity=sev,
                    evidence=attr.factors,
                    thresholds_triggered=thresholds,
                    historical_context=ctx,
                    quality=quality,
                    freshness=freshness,
                    attribution=attr,
                    twin_inputs=twin_inputs,
                    forecast_inputs=forecast_inputs,
                    available_count=self._count_available(twin_inputs, forecast_inputs),
                )
            )

        # Heavy rain hazard
        if report.flood_risk is not None and rainfall is not None:
            ctx = self._historical.get_historical_context(
                location_id,
                "precipitation_mm",
                rainfall,
            )
            attr = build_heavy_rain_attribution(
                rainfall,
                report.flood_risk.multi_day_accumulation,
                100.0,
                report.flood_risk.score,
            )
            score = report.flood_risk.score
            sev = severity_from_score(score, thresholds=self._qc)
            thresholds = []
            if rainfall > 100:
                thresholds.append("rainfall_24h>100mm")
            assessments.append(
                self._build_assessment(
                    location_id=location_id,
                    assessment_type=assessment_type,
                    hazard_type=HazardType.HEAVY_RAIN,
                    score=score,
                    severity=sev,
                    evidence=attr.factors,
                    thresholds_triggered=thresholds,
                    historical_context=ctx,
                    quality=quality,
                    freshness=freshness,
                    attribution=attr,
                    twin_inputs=twin_inputs,
                    forecast_inputs=forecast_inputs,
                    available_count=self._count_available(twin_inputs, forecast_inputs),
                )
            )

        # Dryness hazard
        if report.drought_risk is not None and rainfall is not None:
            attr = build_dryness_attribution(
                rainfall,
                100.0,
                twin_inputs.dry_period_days if twin_inputs else 0,
                report.drought_risk.temperature_anomaly,
            )
            score = report.drought_risk.score
            sev = severity_from_score(score, thresholds=self._qc)
            assessments.append(
                self._build_assessment(
                    location_id=location_id,
                    assessment_type=assessment_type,
                    hazard_type=HazardType.DRYNESS,
                    score=score,
                    severity=sev,
                    evidence=attr.factors,
                    thresholds_triggered=[],
                    historical_context=None,
                    quality=quality,
                    freshness=freshness,
                    attribution=attr,
                    twin_inputs=twin_inputs,
                    forecast_inputs=forecast_inputs,
                    available_count=self._count_available(twin_inputs, forecast_inputs),
                )
            )

        if not assessments:
            return [self._insufficient_data(location_id, "no hazard scored", assessment_type)]

        return assessments

    @staticmethod
    def _count_available(
        twin: TwinInputs | None,
        forecast: ForecastInputs | None,
    ) -> int:
        """Count REAL, non-None inputs available.  Each hazard type
        only counts the fields it actually uses."""
        count = 0
        if twin is not None:
            if twin.max_temp is not None and twin.authenticity == "REAL":
                count += 1
            if twin.rainfall is not None and twin.authenticity == "REAL":
                count += 1
        if forecast is not None:
            if forecast.max_temp is not None and forecast.authenticity == "REAL":
                count += 1
            if forecast.rainfall is not None and forecast.authenticity == "REAL":
                count += 1
        return max(count, 1)

    def _resolve_inputs(
        self,
        twin: TwinInputs | None,
        forecast: ForecastInputs | None,
    ) -> tuple[float | None, float | None, float | None] | None:
        if twin is not None:
            return (twin.max_temp, twin.min_temp, twin.rainfall)
        if forecast is not None:
            return (forecast.max_temp, forecast.min_temp, forecast.rainfall)
        return None

    def _build_assessment(
        self,
        location_id: str,
        assessment_type: AssessmentType,
        hazard_type: HazardType,
        score: float,
        severity: Severity,
        evidence: list[Any],
        thresholds_triggered: list[str],
        historical_context: Any,
        quality: DataQuality,
        freshness: Freshness,
        attribution: Any,
        twin_inputs: TwinInputs | None,
        forecast_inputs: ForecastInputs | None,
        available_count: int = 0,
    ) -> HazardAssessment:
        obs_ids = twin_inputs.observation_ids if twin_inputs else []
        fcast_ids = (
            [forecast_inputs.forecast_id] if forecast_inputs and forecast_inputs.forecast_id else []
        )

        expected = 3
        count = available_count
        conf = compute_confidence(
            quality,
            freshness,
            count,
            expected,
            forecast_validated=(forecast_inputs.physics_validated if forecast_inputs else False),
            config=self._qc,
        )

        provenance: dict[str, str] = {}
        if twin_inputs:
            provenance["twin_authenticity"] = twin_inputs.authenticity
            provenance["twin_data_source"] = twin_inputs.data_source
            provenance["twin_quality_flag"] = twin_inputs.quality_flag
        if forecast_inputs:
            provenance["forecast_id"] = forecast_inputs.forecast_id
            provenance["model_id"] = forecast_inputs.model_id
            provenance["training_run_id"] = forecast_inputs.training_run_id
            provenance["dataset_id"] = forecast_inputs.dataset_id
            provenance["forecast_authenticity"] = forecast_inputs.authenticity

        twin_version = (
            twin_inputs.twin_version
            if twin_inputs
            else (str(forecast_inputs.source_twin_version) if forecast_inputs else None)
        )

        return HazardAssessment(
            hazard_type=hazard_type.value,
            assessment_type=assessment_type,
            location_id=location_id,
            severity=severity,
            hazard_score=round(score, 2),
            assessment_confidence=round(conf, 3),
            source_twin_version=twin_version,
            source_observation_ids=obs_ids,
            source_forecast_ids=fcast_ids,
            evidence=evidence,
            thresholds_triggered=thresholds_triggered,
            historical_context=historical_context,
            data_quality=quality,
            data_freshness=freshness,
            method=f"HAZARD_{hazard_type.value.upper()}_V1",
            method_version="1.0.0",
            config_version=CONFIG_VERSION,
            attribution=attribution,
            provenance=provenance,
        )

    def _insufficient_data(
        self,
        location_id: str,
        reason: str,
        assessment_type: AssessmentType,
    ) -> HazardAssessment:
        return HazardAssessment(
            hazard_type="unknown",
            assessment_type=assessment_type,
            location_id=location_id,
            severity=Severity.NONE,
            hazard_score=0.0,
            assessment_confidence=0.0,
            data_quality=DataQuality.REJECTED,
            data_freshness=Freshness.UNAVAILABLE,
            method="NONE",
            method_version="",
            config_version=CONFIG_VERSION,
            provenance={"reason": reason},
        )

    def process_and_store(
        self,
        twin_inputs: TwinInputs | None,
        forecast_inputs: ForecastInputs | None,
        location_id: str,
    ) -> tuple[list[HazardAssessment], list[Any]]:
        assessments: list[HazardAssessment] = []
        alerts_created: list[Any] = []

        if twin_inputs is not None:
            assessments = self.assess_observed(twin_inputs, location_id)
        elif forecast_inputs is not None:
            assessments = self.assess_forecast(forecast_inputs, location_id)

        if not assessments:
            return assessments, alerts_created

        for assessment in assessments:
            if assessment.hazard_type == "unknown":
                continue
            self._hazard_store.save(assessment)

        primary = max(assessments, key=lambda a: a.hazard_score) if assessments else None
        if primary and primary.hazard_type != "unknown":
            active_alerts = self._alert_store.list_active_by_location(location_id)
            new_alert = self._alert_policy.evaluate(primary, active_alerts)
            if new_alert:
                self._alert_store.save(new_alert)
                alerts_created.append(new_alert)

            resolved = self._alert_policy.resolve(primary, active_alerts)
            for r in resolved:
                self._alert_store.update(r)

        return assessments, alerts_created

    @property
    def hazard_store(self) -> HazardStore:
        return self._hazard_store

    @property
    def alert_store(self) -> AlertStore:
        return self._alert_store
