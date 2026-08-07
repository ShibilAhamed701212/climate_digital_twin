"""Unit tests for SHAP explainer and insights engine."""


class TestGenerateExplanation:
    """Test SHAP explanation generation."""

    def test_generate_basic_explanation(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=65.0,
            feature_values={"max_temp": 40.0, "rainfall": 50.0, "consecutive_hot_days": 5.0},
            prediction_confidence=0.85,
        )
        assert explanation.prediction == 65.0
        assert explanation.base_value == 50.0
        assert len(explanation.feature_attributions) <= 10
        assert len(explanation.top_features) > 0
        assert explanation.risk_interpretation != ""

    def test_positive_and_negative_contributors(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=75.0,
            feature_values={
                "max_temp": 42.0,
                "rainfall": 10.0,
                "dry_period_days": 15.0,
                "consecutive_hot_days": 7.0,
            },
        )
        all_positive = all(a.shap_value >= 0 for a in explanation.positive_contributors)
        all_negative = all(a.shap_value < 0 for a in explanation.negative_contributors)
        assert all_positive
        assert all_negative

    def test_low_prediction_interpretation(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=15.0,
            feature_values={"max_temp": 28.0, "rainfall": 150.0},
        )
        assert "Very Low" in explanation.risk_interpretation

    def test_high_prediction_interpretation(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=85.0,
            feature_values={"max_temp": 45.0, "rainfall": 5.0, "dry_period_days": 30.0},
        )
        assert "Severe" in explanation.risk_interpretation
        assert "risk score is 85" in explanation.risk_interpretation

    def test_config_accepts_custom_max_features(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=50.0,
            feature_values={"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": 5.0},
            config={"max_display_features": 3},
        )
        assert len(explanation.feature_attributions) <= 3

    def test_all_feature_values_zero(self):
        from risk.explainability.shap_explainer import generate_explanation

        explanation = generate_explanation(
            prediction=50.0,
            feature_values={"max_temp": 0.0, "rainfall": 0.0},
        )
        assert explanation.prediction == 50.0


class TestGlobalFeatureImportance:
    """Test global feature importance aggregation."""

    def test_single_explanation(self):
        from risk.explainability.shap_explainer import (
            generate_explanation,
            get_global_feature_importance,
        )

        exp = generate_explanation(60.0, {"max_temp": 38.0, "rainfall": 50.0})
        result = get_global_feature_importance([exp])
        assert len(result) > 0
        assert all(r.mean_abs_shap >= 0 for r in result)

    def test_multiple_explanations_aggregated(self):
        from risk.explainability.shap_explainer import (
            generate_explanation,
            get_global_feature_importance,
        )

        exp1 = generate_explanation(70.0, {"max_temp": 40.0, "rainfall": 30.0})
        exp2 = generate_explanation(30.0, {"max_temp": 32.0, "rainfall": 120.0})
        result = get_global_feature_importance([exp1, exp2])
        features = {r.feature_name for r in result}
        assert "max_temp" in features
        assert "rainfall" in features


class TestInsightsEngine:
    """Test climate insights generation."""

    def test_generate_insights(self):
        from risk.explainability.insights_engine import generate_insights
        from risk.scoring import calculate_drought_risk, calculate_flood_risk, calculate_heat_risk
        from risk.scoring.composite_risk import calculate_composite_risk

        heat = calculate_heat_risk(max_temp=40.0, consecutive_hot_days=5, seasonal_anomaly=3.0)
        flood = calculate_flood_risk(rainfall=150.0)
        drought = calculate_drought_risk(
            rainfall=30.0, historical_mean_rainfall=100.0, max_temp=38.0, dry_period_days=10
        )
        composite = calculate_composite_risk(heat.score, flood.score, drought.score)

        insights = generate_insights(heat, flood, drought, composite)
        assert len(insights) > 0
        for insight in insights:
            assert insight.variable != ""
            assert insight.description != ""
            assert insight.risk_implication != ""

    def test_no_risk_no_insights(self):
        from risk.explainability.insights_engine import generate_insights
        from risk.scoring import calculate_drought_risk, calculate_flood_risk, calculate_heat_risk
        from risk.scoring.composite_risk import calculate_composite_risk

        heat = calculate_heat_risk(max_temp=25.0)
        flood = calculate_flood_risk(rainfall=10.0)
        drought = calculate_drought_risk(rainfall=100.0, historical_mean_rainfall=100.0)
        composite = calculate_composite_risk(heat.score, flood.score, drought.score)

        insights = generate_insights(heat, flood, drought, composite)
        assert len(insights) >= 1  # composite insight always generated

    def test_composite_insight_identifies_primary_risk(self):
        from risk.explainability.insights_engine import generate_insights
        from risk.scoring import calculate_drought_risk, calculate_flood_risk, calculate_heat_risk
        from risk.scoring.composite_risk import calculate_composite_risk

        heat = calculate_heat_risk(max_temp=45.0, consecutive_hot_days=10)
        flood = calculate_flood_risk(rainfall=30.0)
        drought = calculate_drought_risk(rainfall=80.0, historical_mean_rainfall=100.0)
        composite = calculate_composite_risk(heat.score, flood.score, drought.score)

        insights = generate_insights(heat, flood, drought, composite)
        composite_insights = [i for i in insights if i.variable == "composite"]
        assert len(composite_insights) >= 1
        assert "Heat" in composite_insights[0].description
