"""Climate Risk Engine — orchestrates risk assessment computations.

Coordinates scoring modules, SHAP explainability, and report generation.
"""

import logging
from typing import Any

import yaml

from risk.explainability.insights_engine import generate_insights
from risk.explainability.shap_explainer import generate_explanation
from risk.models.agriculture_risk import AgricultureRiskModel
from risk.models.risk_models import (
    ClimateInsight,
    CompositeRiskScore,
    DroughtRiskScore,
    FloodRiskScore,
    HeatRiskScore,
    RiskReport,
    RiskScore,
    SHAPExplanation,
)
from risk.reports.report_generator import generate_report
from risk.scoring import (
    calculate_composite_risk,
    calculate_drought_risk,
    calculate_flood_risk,
    calculate_heat_risk,
)

logger = logging.getLogger(__name__)


class RiskEngine:
    """Orchestrates risk assessment for climate entities.

    Accepts climate data, computes all risk scores, generates SHAP
    explanations, produces climate insights, and creates reports.
    """

    def __init__(self, config_path: str = "risk/configs/risk.yaml") -> None:
        self.config_path = config_path
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self._validate_config()

    def _validate_config(self) -> None:
        required_keys = ["risk", "heat", "flood", "drought", "composite", "shap", "output"]
        for key in required_keys:
            if key not in self.config:
                logger.warning("Missing config key: %s — using defaults", key)

    @property
    def heat_config(self) -> dict[str, Any]:
        return self.config.get("heat", {})

    @property
    def flood_config(self) -> dict[str, Any]:
        return self.config.get("flood", {})

    @property
    def drought_config(self) -> dict[str, Any]:
        return self.config.get("drought", {})

    @property
    def composite_config(self) -> dict[str, Any]:
        return self.config.get("composite", {})

    @property
    def shap_config(self) -> dict[str, Any]:
        return self.config.get("shap", {})

    @property
    def output_config(self) -> dict[str, Any]:
        return self.config.get("output", {})

    def assess_all(
        self,
        location_id: str,
        district: str,
        max_temp: float,
        min_temp: float,
        rainfall: float,
        historical_mean_rainfall: float = 100.0,
        historical_mean_temp: float = 28.0,
        consecutive_hot_days: int = 0,
        dry_period_days: int = 0,
        multi_day_accumulation: float | None = None,
        seasonal_anomaly: float = 0.0,
        forecast_uncertainty: float = 0.0,
        prediction_confidence: float = 0.0,
        agriculture_features: dict[str, float | str] | None = None,
    ) -> RiskReport:
        """Compute all risk scores, explanations, and insights for a location.

        Args:
            location_id: Unique location identifier.
            district: District name.
            max_temp: Maximum temperature in Celsius.
            min_temp: Minimum temperature in Celsius.
            rainfall: Current rainfall in mm.
            historical_mean_rainfall: Long-term average rainfall.
            historical_mean_temp: Long-term average max temperature.
            consecutive_hot_days: Number of consecutive hot days.
            dry_period_days: Number of consecutive dry days.
            multi_day_accumulation: Multi-day rainfall accumulation.
            seasonal_anomaly: Temperature anomaly from seasonal norm.
            forecast_uncertainty: Forecast uncertainty (0-1).
            prediction_confidence: Prediction confidence (0-1).

        Returns:
            RiskReport with all risk scores, explanation, and insights.
        """
        logger.info("Assessing risk for %s (%s)", location_id, district)

        heat = self.assess_heat_risk(max_temp, consecutive_hot_days, seasonal_anomaly)
        flood = self.assess_flood_risk(rainfall, multi_day_accumulation, forecast_uncertainty)
        drought = self.assess_drought_risk(
            rainfall, historical_mean_rainfall, max_temp, historical_mean_temp, dry_period_days
        )
        composite = self.assess_composite_risk(heat.score, flood.score, drought.score)
        agriculture = (
            self.assess_agriculture_risk(location_id, agriculture_features)
            if agriculture_features
            else None
        )

        explanation = self._generate_explanation(
            prediction=composite.score,
            feature_values={
                "max_temp": max_temp,
                "rainfall": rainfall,
                "consecutive_hot_days": float(consecutive_hot_days),
                "dry_period_days": float(dry_period_days),
                "seasonal_anomaly": seasonal_anomaly,
                "forecast_uncertainty": forecast_uncertainty,
            },
            prediction_confidence=prediction_confidence,
        )

        insights = self._generate_insights(
            heat=heat,
            flood=flood,
            drought=drought,
            composite=composite,
        )

        report = RiskReport(
            location_id=location_id,
            district=district,
            heat_risk=heat,
            flood_risk=flood,
            drought_risk=drought,
            composite_risk=composite,
            agriculture_risk=agriculture,
            explanation=explanation,
            insights=insights,
            raw_data={
                "max_temp": max_temp,
                "min_temp": min_temp,
                "rainfall": rainfall,
                "consecutive_hot_days": consecutive_hot_days,
                "dry_period_days": dry_period_days,
                "seasonal_anomaly": seasonal_anomaly,
                "forecast_uncertainty": forecast_uncertainty,
                "prediction_confidence": prediction_confidence,
            },
        )

        return report

    def assess_heat_risk(
        self,
        max_temp: float,
        consecutive_hot_days: int = 0,
        seasonal_anomaly: float = 0.0,
    ) -> HeatRiskScore:
        return calculate_heat_risk(
            max_temp=max_temp,
            consecutive_hot_days=consecutive_hot_days,
            seasonal_anomaly=seasonal_anomaly,
            weights=self.heat_config.get("weights"),
            hot_day_threshold=self.heat_config.get("hot_day_threshold_c", 35),
            consecutive_days_threshold=self.heat_config.get("consecutive_days_threshold", 3),
        )

    def assess_flood_risk(
        self,
        rainfall: float,
        multi_day_accumulation: float | None = None,
        forecast_uncertainty: float = 0.0,
    ) -> FloodRiskScore:
        return calculate_flood_risk(
            rainfall=rainfall,
            multi_day_accumulation=multi_day_accumulation,
            forecast_uncertainty=forecast_uncertainty,
            weights=self.flood_config.get("weights"),
            heavy_rain_threshold=self.flood_config.get("heavy_rain_threshold_mm", 100),
            accumulation_window_days=self.flood_config.get("accumulation_window_days", 3),
        )

    def assess_drought_risk(
        self,
        rainfall: float,
        historical_mean_rainfall: float = 100.0,
        max_temp: float = 30.0,
        historical_mean_temp: float = 28.0,
        dry_period_days: int = 0,
    ) -> DroughtRiskScore:
        return calculate_drought_risk(
            rainfall=rainfall,
            historical_mean_rainfall=historical_mean_rainfall,
            max_temp=max_temp,
            historical_mean_temp=historical_mean_temp,
            dry_period_days=dry_period_days,
            weights=self.drought_config.get("weights"),
            deficit_threshold_percent=self.drought_config.get("deficit_threshold_percent", -25),
            dry_period_threshold_days=self.drought_config.get("dry_period_threshold_days", 15),
        )

    def assess_composite_risk(
        self,
        heat_score: float,
        flood_score: float,
        drought_score: float,
    ) -> CompositeRiskScore:
        return calculate_composite_risk(
            heat_score=heat_score,
            flood_score=flood_score,
            drought_score=drought_score,
            weights=self.composite_config.get("weights"),
        )

    def assess_agriculture_risk(
        self,
        location_id: str,
        features: dict[str, float | str] | None = None,
    ) -> RiskScore | None:
        if not features:
            return None
        model = AgricultureRiskModel()
        import asyncio

        return asyncio.run(model.assess(location_id=location_id, **features))

    def _generate_explanation(
        self,
        prediction: float,
        feature_values: dict[str, float],
        prediction_confidence: float = 0.0,
    ) -> SHAPExplanation:
        return generate_explanation(
            prediction=prediction,
            feature_values=feature_values,
            prediction_confidence=prediction_confidence,
            config=self.shap_config,
        )

    def _generate_insights(
        self,
        heat: HeatRiskScore,
        flood: FloodRiskScore,
        drought: DroughtRiskScore,
        composite: CompositeRiskScore,
    ) -> list[ClimateInsight]:
        return generate_insights(heat=heat, flood=flood, drought=drought, composite=composite)

    def generate_full_report(
        self,
        location_id: str,
        district: str,
        report: RiskReport,
        formats: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate and save risk report in specified formats.

        Args:
            location_id: Unique location identifier.
            district: District name.
            report: RiskReport to serialize.
            formats: List of output formats (default from config).

        Returns:
            Dict mapping format to output file path.
        """
        fmt = formats or self.output_config.get("formats", ["json", "markdown"])
        output_dir = self.output_config.get("output_dir", "risk/outputs")
        return generate_report(
            location_id=location_id,
            district=district,
            report=report,
            output_dir=output_dir,
            formats=fmt,
        )
