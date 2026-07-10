"""Tests for risk/explainability/insights_engine.py."""

from risk.explainability.insights_engine import (
    _composite_insights,
    _drought_insights,
    _flood_insights,
    _heat_insights,
    _risk_label,
    generate_insights,
)
from risk.models.risk_models import (
    ClimateInsight,
    CompositeRiskScore,
    DroughtRiskScore,
    FloodRiskScore,
    HeatRiskScore,
)


class TestRiskLabel:
    def test_very_low(self):
        assert _risk_label(0) == "Very Low"
        assert _risk_label(20) == "Very Low"

    def test_low(self):
        assert _risk_label(21) == "Low"
        assert _risk_label(40) == "Low"

    def test_moderate(self):
        assert _risk_label(41) == "Moderate"
        assert _risk_label(60) == "Moderate"

    def test_high(self):
        assert _risk_label(61) == "High"
        assert _risk_label(80) == "High"

    def test_severe(self):
        assert _risk_label(81) == "Severe"
        assert _risk_label(100) == "Severe"


class TestFloodInsights:
    def test_multi_day_accumulation_over_200(self):
        flood = FloodRiskScore(
            score=50,
            rainfall_intensity_contribution=10,
            multi_day_accumulation_contribution=20,
            forecast_uncertainty_contribution=5,
            multi_day_accumulation=250,
            rainfall_intensity=50,
        )
        insights = _flood_insights(flood)
        assert any("Multi-day accumulation" in i.description for i in insights)

    def test_both_thresholds_triggered(self):
        flood = FloodRiskScore(
            score=50,
            rainfall_intensity_contribution=10,
            multi_day_accumulation_contribution=20,
            forecast_uncertainty_contribution=5,
            multi_day_accumulation=250,
            rainfall_intensity=150,
        )
        insights = _flood_insights(flood)
        assert len(insights) == 2


class TestCompositeInsights:
    def test_primary_flood(self):
        heat = HeatRiskScore(
            score=30,
            max_temperature_contribution=10,
            consecutive_hot_days_contribution=10,
            seasonal_anomaly_contribution=10,
            consecutive_hot_days=0,
            seasonal_anomaly=0,
        )
        flood = FloodRiskScore(
            score=80,
            rainfall_intensity_contribution=30,
            multi_day_accumulation_contribution=30,
            forecast_uncertainty_contribution=20,
            multi_day_accumulation=100,
            rainfall_intensity=80,
        )
        drought = DroughtRiskScore(
            score=20,
            rainfall_deficit_contribution=10,
            temperature_increase_contribution=5,
            dry_period_days_contribution=5,
            rainfall_deficit_percent=0,
            temperature_anomaly=0,
        )
        composite = CompositeRiskScore(
            score=60,
            heat_score=30,
            flood_score=80,
            drought_score=20,
            weights={},
        )
        insights = _composite_insights(composite, heat, flood, drought)
        assert any("Flood" in i.description for i in insights)

    def test_composite_score_over_60_adds_critical(self):
        heat = HeatRiskScore(
            score=50,
            max_temperature_contribution=10,
            consecutive_hot_days_contribution=10,
            seasonal_anomaly_contribution=10,
            consecutive_hot_days=0,
            seasonal_anomaly=0,
        )
        flood = FloodRiskScore(
            score=30,
            rainfall_intensity_contribution=10,
            multi_day_accumulation_contribution=10,
            forecast_uncertainty_contribution=10,
            multi_day_accumulation=50,
            rainfall_intensity=50,
        )
        drought = DroughtRiskScore(
            score=20,
            rainfall_deficit_contribution=10,
            temperature_increase_contribution=5,
            dry_period_days_contribution=5,
            rainfall_deficit_percent=0,
            temperature_anomaly=0,
        )
        composite = CompositeRiskScore(
            score=75,
            heat_score=50,
            flood_score=30,
            drought_score=20,
            weights={},
        )
        insights = _composite_insights(composite, heat, flood, drought)
        assert any("critical" in i.direction for i in insights)


class TestHeatInsights:
    def test_seasonal_anomaly_above_2(self):
        heat = HeatRiskScore(
            score=50,
            max_temperature_contribution=10,
            consecutive_hot_days_contribution=10,
            seasonal_anomaly_contribution=10,
            consecutive_hot_days=0,
            seasonal_anomaly=3.0,
        )
        insights = _heat_insights(heat)
        assert any("above seasonal average" in i.description for i in insights)

    def test_consecutive_hot_days_above_3(self):
        heat = HeatRiskScore(
            score=50,
            max_temperature_contribution=10,
            consecutive_hot_days_contribution=10,
            seasonal_anomaly_contribution=10,
            consecutive_hot_days=5,
            seasonal_anomaly=0,
        )
        insights = _heat_insights(heat)
        assert any("consecutive hot days" in i.description for i in insights)


class TestDroughtInsights:
    def test_rainfall_deficit_below_25(self):
        drought = DroughtRiskScore(
            score=50,
            rainfall_deficit_contribution=20,
            temperature_increase_contribution=10,
            dry_period_days_contribution=5,
            rainfall_deficit_percent=-30,
            temperature_anomaly=0,
        )
        insights = _drought_insights(drought)
        assert any("deficit" in i.direction for i in insights)

    def test_temperature_anomaly_above_1_5(self):
        drought = DroughtRiskScore(
            score=50,
            rainfall_deficit_contribution=10,
            temperature_increase_contribution=10,
            dry_period_days_contribution=5,
            rainfall_deficit_percent=0,
            temperature_anomaly=2.0,
        )
        insights = _drought_insights(drought)
        assert any("above normal" in i.description for i in insights)


class TestCompositeInsightsExtended:
    def test_primary_drought(self):
        heat = HeatRiskScore(
            score=20,
            max_temperature_contribution=5,
            consecutive_hot_days_contribution=5,
            seasonal_anomaly_contribution=5,
            consecutive_hot_days=0,
            seasonal_anomaly=0,
        )
        flood = FloodRiskScore(
            score=30,
            rainfall_intensity_contribution=10,
            multi_day_accumulation_contribution=10,
            forecast_uncertainty_contribution=10,
            multi_day_accumulation=50,
            rainfall_intensity=50,
        )
        drought = DroughtRiskScore(
            score=80,
            rainfall_deficit_contribution=30,
            temperature_increase_contribution=20,
            dry_period_days_contribution=10,
            rainfall_deficit_percent=0,
            temperature_anomaly=0,
        )
        composite = CompositeRiskScore(
            score=50,
            heat_score=20,
            flood_score=30,
            drought_score=80,
            weights={},
        )
        insights = _composite_insights(composite, heat, flood, drought)
        assert any("Drought" in i.description for i in insights)


class TestGenerateInsights:
    def test_generate_insights_includes_all_types(self):
        heat = HeatRiskScore(
            score=50,
            max_temperature_contribution=10,
            consecutive_hot_days_contribution=10,
            seasonal_anomaly_contribution=10,
            consecutive_hot_days=0,
            seasonal_anomaly=0,
        )
        flood = FloodRiskScore(
            score=30,
            rainfall_intensity_contribution=10,
            multi_day_accumulation_contribution=10,
            forecast_uncertainty_contribution=10,
            multi_day_accumulation=50,
            rainfall_intensity=50,
        )
        drought = DroughtRiskScore(
            score=20,
            rainfall_deficit_contribution=10,
            temperature_increase_contribution=5,
            dry_period_days_contribution=5,
            rainfall_deficit_percent=0,
            temperature_anomaly=0,
        )
        composite = CompositeRiskScore(
            score=40,
            heat_score=50,
            flood_score=30,
            drought_score=20,
            weights={},
        )
        insights = generate_insights(heat, flood, drought, composite)
        assert len(insights) >= 1
        assert all(isinstance(i, ClimateInsight) for i in insights)
