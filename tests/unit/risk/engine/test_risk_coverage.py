"""Edge case coverage for risk engine, scoring, and explainability modules."""


import yaml

from risk.models.risk_models import RiskReport
from risk.scoring.composite_risk import calculate_composite_risk
from risk.scoring.drought_risk import (
    _deficit_score,
    _dry_period_score,
    _temperature_drought_score,
    calculate_drought_risk,
)
from risk.scoring.flood_risk import (
    _accumulation_score,
    _intensity_score,
    _uncertainty_score,
    calculate_flood_risk,
)
from risk.scoring.heat_risk import (
    _anomaly_score,
    _consecutive_days_score,
    _temperature_score,
    calculate_heat_risk,
)


def _make_config(**overrides):
    base = {
        "risk": {},
        "heat": {},
        "flood": {},
        "drought": {},
        "composite": {},
        "shap": {},
        "output": {},
    }
    base.update(overrides)
    return base


class TestHeatRiskEdgeCases:
    def test_temperature_score_exact_threshold(self):
        assert _temperature_score(35.0, 35.0) == 0.0

    def test_temperature_score_above(self):
        assert _temperature_score(40.0, 35.0) == 20.0

    def test_consecutive_days_score_zero(self):
        assert _consecutive_days_score(0, 3) == 0.0

    def test_consecutive_days_score_above_threshold(self):
        assert _consecutive_days_score(5, 3) == 60.0

    def test_anomaly_score_zero(self):
        assert _anomaly_score(0) == 0.0

    def test_anomaly_score_positive(self):
        assert _anomaly_score(2.0) == 30.0

    def test_heat_risk_default_weights(self):
        score = calculate_heat_risk(max_temp=38.0, consecutive_hot_days=3, seasonal_anomaly=1.0)
        assert 0 <= score.score <= 100


class TestFloodRiskEdgeCases:
    def test_intensity_score_zero(self):
        assert _intensity_score(0, 100) == 0.0

    def test_intensity_score_below_threshold(self):
        assert _intensity_score(80, 100) == 40.0

    def test_accumulation_score_zero(self):
        assert _accumulation_score(0, 100, 3) == 0.0

    def test_uncertainty_score_zero(self):
        assert _uncertainty_score(0) == 0.0

    def test_flood_risk_none_accumulation(self):
        outcome = calculate_flood_risk(rainfall=50.0, multi_day_accumulation=None)
        assert outcome.score >= 0

    def test_flood_risk_custom_weights(self):
        outcome = calculate_flood_risk(
            rainfall=150.0,
            weights={
                "rainfall_intensity": 1.0,
                "multi_day_accumulation": 0.0,
                "forecast_uncertainty": 0.0,
            },
        )
        assert outcome.score > 0


class TestDroughtRiskEdgeCases:
    def test_deficit_score_surplus(self):
        assert _deficit_score(10.0, -25) == 0.0

    def test_deficit_score_below_threshold(self):
        assert _deficit_score(-50.0, -25) > 40.0

    def test_temp_drought_score_zero(self):
        assert _temperature_drought_score(0) == 0.0

    def test_dry_period_score_zero(self):
        assert _dry_period_score(0, 15) == 0.0

    def test_dry_period_score_below_threshold(self):
        score = _dry_period_score(10, 15)
        assert 0 < score <= 40

    def test_drought_risk_custom_weights(self):
        outcome = calculate_drought_risk(
            rainfall=80.0,
            weights={"rainfall_deficit": 1.0, "temperature_increase": 0.0, "dry_period_days": 0.0},
        )
        assert outcome.score >= 0


class TestCompositeRiskEdgeCases:
    def test_composite_custom_weights(self):
        outcome = calculate_composite_risk(
            heat_score=50,
            flood_score=30,
            drought_score=20,
            weights={"heat": 0.5, "flood": 0.3, "drought": 0.2},
        )
        assert outcome.score > 0

    def test_composite_default_weights(self):
        outcome = calculate_composite_risk(heat_score=100, flood_score=0, drought_score=0)
        assert 32 <= outcome.score <= 34


class TestGenerateReport:
    def test_report_to_dict(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        report = engine.assess_all("loc-001", "Test", max_temp=35.0, min_temp=22.0, rainfall=80.0)
        d = report.to_dict()
        assert d["location_id"] == "loc-001"
        assert "heat_risk" in d

    def test_full_report_generation(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        report = engine.assess_all("loc-001", "Test", max_temp=35.0, min_temp=22.0, rainfall=80.0)
        out = engine.generate_full_report("loc-001", "Test", report, formats=["json"])
        assert "json" in out


class TestSHAPExplainer:
    def test_generate_explanation_basic(self):
        from risk.explainability.shap_explainer import generate_explanation

        exp = generate_explanation(60.0, {"max_temp": 38.0, "rainfall": 80.0})
        assert exp.prediction == 60.0
        assert len(exp.feature_attributions) == 2

    def test_generate_explanation_with_confidence(self):
        from risk.explainability.shap_explainer import generate_explanation

        exp = generate_explanation(45.0, {"max_temp": 35.0}, prediction_confidence=0.8)
        assert exp.confidence == 0.8

    def test_global_importance(self):
        from risk.explainability.shap_explainer import (
            generate_explanation,
            get_global_feature_importance,
        )

        exp1 = generate_explanation(60.0, {"max_temp": 38.0, "rainfall": 120.0})
        exp2 = generate_explanation(30.0, {"max_temp": 32.0, "rainfall": 50.0})
        gi = get_global_feature_importance([exp1, exp2])
        assert len(gi) == 2
        names = [g.feature_name for g in gi]
        assert "max_temp" in names

    def test_global_importance_with_feature_names(self):
        from risk.explainability.shap_explainer import (
            generate_explanation,
            get_global_feature_importance,
        )

        exp = generate_explanation(50.0, {"max_temp": 35.0})
        gi = get_global_feature_importance([exp], feature_names=["max_temp", "rainfall"])
        assert len(gi) == 2


class TestGenerateFullReportEdgeCases:
    def test_empty_formats_defaults(self, tmp_path):
        from risk.reports.report_generator import generate_report

        report = RiskReport(location_id="loc-test", district="D")
        out = generate_report("loc-test", "D", report, output_dir=str(tmp_path), formats=None)
        assert "json" in out and "markdown" in out

    def test_markdown_format(self, tmp_path):
        from risk.reports.report_generator import generate_report

        report = RiskReport(location_id="loc-md", district="MD")
        out = generate_report(
            "loc-md", "MD", report, output_dir=str(tmp_path), formats=["markdown"]
        )
        assert "markdown" in out


class TestAgricultureRiskModel:
    def test_compute_raw_no_features(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        assert AgricultureRiskModel()._compute_raw_score({}) == 50.0

    def test_compute_with_all_features(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        score = AgricultureRiskModel()._compute_raw_score(
            {
                "growing_season_temp": 25.0,
                "growing_season_precip": 100.0,
                "precipitation_deficit": 10.0,
                "temperature_stress_days": 2,
                "soil_moisture": 0.3,
                "ndvi": 0.6,
                "monsoon_performance": 0.8,
            }
        )
        assert 0 <= score <= 100

    def test_temp_stress_frost(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        assert AgricultureRiskModel._temperature_stress_score(-1.0) == 100.0

    def test_temp_stress_below_optimal(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        assert 0 < AgricultureRiskModel._temperature_stress_score(10.0) < 100

    def test_precip_adequacy_drought(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        assert AgricultureRiskModel._precipitation_adequacy_score(5.0) == 100.0

    def test_precip_adequacy_surplus(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        assert AgricultureRiskModel._precipitation_adequacy_score(300.0) == 50.0

    def test_generate_description_extreme(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        desc = AgricultureRiskModel._generate_description(85, {"crop_stage": "flowering"})
        assert "Extreme" in desc or "Urgent" in desc
