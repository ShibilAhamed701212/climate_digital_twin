"""Unit tests for risk data models."""

import pytest


class TestRiskCategory:
    """Test risk categorization logic."""

    def test_categorize_very_low(self):
        from risk.models.risk_models import categorize_risk

        assert categorize_risk(0).value == "Very Low"
        assert categorize_risk(10).value == "Very Low"
        assert categorize_risk(20).value == "Very Low"

    def test_categorize_low(self):
        from risk.models.risk_models import categorize_risk

        assert categorize_risk(21).value == "Low"
        assert categorize_risk(30).value == "Low"
        assert categorize_risk(40).value == "Low"

    def test_categorize_moderate(self):
        from risk.models.risk_models import categorize_risk

        assert categorize_risk(41).value == "Moderate"
        assert categorize_risk(50).value == "Moderate"
        assert categorize_risk(60).value == "Moderate"

    def test_categorize_high(self):
        from risk.models.risk_models import categorize_risk

        assert categorize_risk(61).value == "High"
        assert categorize_risk(70).value == "High"
        assert categorize_risk(80).value == "High"

    def test_categorize_severe(self):
        from risk.models.risk_models import categorize_risk

        assert categorize_risk(81).value == "Severe"
        assert categorize_risk(95).value == "Severe"
        assert categorize_risk(100).value == "Severe"


class TestHeatRiskScore:
    """Test HeatRiskScore dataclass."""

    def test_create_heat_risk_score(self):
        from risk.models.risk_models import HeatRiskScore

        h = HeatRiskScore(
            score=45.5,
            max_temperature_contribution=30.0,
            consecutive_hot_days_contribution=10.0,
            seasonal_anomaly_contribution=5.5,
            consecutive_hot_days=5,
            seasonal_anomaly=2.3,
        )
        assert h.score == 45.5
        assert h.consecutive_hot_days == 5
        assert h.seasonal_anomaly == 2.3

    def test_heat_risk_immutable(self):
        from risk.models.risk_models import HeatRiskScore

        h = HeatRiskScore(10, 5, 3, 2, 1, 0.5)
        with pytest.raises(AttributeError):
            h.score = 99


class TestFloodRiskScore:
    """Test FloodRiskScore dataclass."""

    def test_create_flood_risk_score(self):
        from risk.models.risk_models import FloodRiskScore

        f = FloodRiskScore(
            score=60.0,
            rainfall_intensity_contribution=30.0,
            multi_day_accumulation_contribution=20.0,
            forecast_uncertainty_contribution=10.0,
            multi_day_accumulation=150.0,
            rainfall_intensity=80.0,
        )
        assert f.score == 60.0
        assert f.multi_day_accumulation == 150.0


class TestDroughtRiskScore:
    """Test DroughtRiskScore dataclass."""

    def test_create_drought_risk_score(self):
        from risk.models.risk_models import DroughtRiskScore

        d = DroughtRiskScore(
            score=55.0,
            rainfall_deficit_contribution=25.0,
            temperature_increase_contribution=15.0,
            dry_period_days_contribution=15.0,
            rainfall_deficit_percent=-30.0,
            temperature_anomaly=2.0,
        )
        assert d.score == 55.0
        assert d.rainfall_deficit_percent == -30.0


class TestCompositeRiskScore:
    """Test CompositeRiskScore dataclass."""

    def test_create_composite(self):
        from risk.models.risk_models import CompositeRiskScore

        c = CompositeRiskScore(
            score=50.0,
            heat_score=60.0,
            flood_score=40.0,
            drought_score=50.0,
            weights={"heat": 0.33, "flood": 0.33, "drought": 0.34},
        )
        assert c.score == 50.0
        assert c.weights["heat"] == 0.33


class TestFeatureAttribution:
    """Test FeatureAttribution dataclass."""

    def test_create(self):
        from risk.models.risk_models import FeatureAttribution

        fa = FeatureAttribution(
            feature_name="max_temp",
            shap_value=2.5,
            feature_value=38.0,
            contribution_type="positive",
        )
        assert fa.feature_name == "max_temp"
        assert fa.shap_value == 2.5

    def test_negative_contribution(self):
        from risk.models.risk_models import FeatureAttribution

        fa = FeatureAttribution("rainfall", -1.2, 50.0, "negative")
        assert fa.contribution_type == "negative"


class TestSHAPExplanation:
    """Test SHAPExplanation dataclass."""

    def test_create(self):
        from risk.models.risk_models import FeatureAttribution, SHAPExplanation

        attrs = [
            FeatureAttribution("max_temp", 3.0, 38.0, "positive"),
            FeatureAttribution("rainfall", -1.0, 50.0, "negative"),
        ]
        exp = SHAPExplanation(
            prediction=65.0,
            base_value=50.0,
            feature_attributions=attrs,
            top_features=["max_temp", "rainfall"],
            positive_contributors=[attrs[0]],
            negative_contributors=[attrs[1]],
            confidence=0.85,
            risk_interpretation="High risk due to elevated temperatures.",
        )
        assert exp.prediction == 65.0
        assert len(exp.positive_contributors) == 1


class TestClimateInsight:
    """Test ClimateInsight dataclass."""

    def test_create(self):
        from risk.models.risk_models import ClimateInsight

        ci = ClimateInsight(
            variable="max_temp",
            direction="increasing",
            magnitude=2.5,
            description="Temperature is 2.5C above average.",
            risk_implication="Increased heat stress risk.",
        )
        assert ci.variable == "max_temp"
        assert ci.magnitude == 2.5


class TestRiskReport:
    """Test RiskReport dataclass."""

    def test_create_minimal(self):
        from risk.models.risk_models import RiskReport

        r = RiskReport(location_id="KA-BLR-001", district="Bangalore")
        assert r.location_id == "KA-BLR-001"
        assert r.heat_risk is None

    def test_to_dict(self):
        from risk.models.risk_models import RiskReport

        r = RiskReport(location_id="KA-BLR-001", district="Bangalore")
        d = r.to_dict()
        assert d["location_id"] == "KA-BLR-001"
        assert d["district"] == "Bangalore"
