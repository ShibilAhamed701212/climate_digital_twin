"""Unit tests for the RiskEngine orchestrator."""

import os
import tempfile

import pytest
import yaml


class TestRiskEngine:
    """Test RiskEngine initialization and core methods."""

    @pytest.fixture
    def minimal_config(self):
        cfg = {
            "risk": {"score_range": {"min": 0, "max": 100}, "categories": []},
            "heat": {
                "weights": {
                    "max_temperature": 0.4,
                    "consecutive_hot_days": 0.35,
                    "seasonal_anomaly": 0.25,
                },
                "hot_day_threshold_c": 35,
                "consecutive_days_threshold": 3,
            },
            "flood": {
                "weights": {
                    "rainfall_intensity": 0.4,
                    "multi_day_accumulation": 0.35,
                    "forecast_uncertainty": 0.25,
                },
                "heavy_rain_threshold_mm": 100,
                "accumulation_window_days": 3,
            },
            "drought": {
                "weights": {
                    "rainfall_deficit": 0.4,
                    "temperature_increase": 0.3,
                    "dry_period_days": 0.3,
                },
                "deficit_threshold_percent": -25,
                "dry_period_threshold_days": 15,
            },
            "composite": {"weights": {"heat": 0.33, "flood": 0.33, "drought": 0.34}},
            "shap": {
                "enabled": True,
                "random_seed": 42,
                "max_display_features": 10,
                "background_samples": 100,
            },
            "output": {"formats": ["json", "markdown"], "output_dir": "risk/outputs"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(cfg, f)
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_engine_initializes(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        assert engine.heat_config["hot_day_threshold_c"] == 35

    def test_assess_heat_risk(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        result = engine.assess_heat_risk(max_temp=40.0)
        assert 0 <= result.score <= 100
        assert result.max_temperature_contribution > 0

    def test_assess_flood_risk(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        result = engine.assess_flood_risk(rainfall=150.0)
        assert 0 <= result.score <= 100

    def test_assess_drought_risk(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        result = engine.assess_drought_risk(rainfall=30.0, historical_mean_rainfall=100.0)
        assert 0 <= result.score <= 100

    def test_assess_composite_risk(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        result = engine.assess_composite_risk(heat_score=50.0, flood_score=30.0, drought_score=20.0)
        assert 0 <= result.score <= 100

    def test_assess_all_produces_report(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        report = engine.assess_all(
            location_id="KA-BLR-001",
            district="Bangalore",
            max_temp=38.0,
            min_temp=20.0,
            rainfall=80.0,
            consecutive_hot_days=5,
            dry_period_days=3,
            seasonal_anomaly=2.0,
            forecast_uncertainty=0.3,
            prediction_confidence=0.85,
        )
        assert report.location_id == "KA-BLR-001"
        assert report.heat_risk is not None
        assert report.flood_risk is not None
        assert report.drought_risk is not None
        assert report.composite_risk is not None
        assert report.explanation is not None
        assert len(report.insights) > 0
        for score in [
            report.heat_risk.score,
            report.flood_risk.score,
            report.drought_risk.score,
            report.composite_risk.score,
        ]:
            assert 0 <= score <= 100

    def test_generate_full_report_files(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        report = engine.assess_all(
            location_id="KA-BLR-001",
            district="Bangalore",
            max_temp=38.0,
            min_temp=20.0,
            rainfall=80.0,
        )
        output_dir = tempfile.mkdtemp()
        engine.output_config["output_dir"] = output_dir
        result = engine.generate_full_report(
            "KA-BLR-001", "Bangalore", report, formats=["json", "markdown"]
        )
        assert "json" in result
        assert "markdown" in result
        assert os.path.exists(result["json"])
        assert os.path.exists(result["markdown"])

    def test_assess_all_extreme_values(self, minimal_config):
        from risk.engine.risk_engine import RiskEngine

        engine = RiskEngine(config_path=minimal_config)
        report = engine.assess_all(
            location_id="KA-HSP-001",
            district="Hassan",
            max_temp=48.0,
            min_temp=30.0,
            rainfall=0.0,
            consecutive_hot_days=15,
            dry_period_days=60,
            historical_mean_rainfall=100.0,
            historical_mean_temp=28.0,
            seasonal_anomaly=5.0,
            forecast_uncertainty=0.9,
        )
        assert report.composite_risk.score > 50
