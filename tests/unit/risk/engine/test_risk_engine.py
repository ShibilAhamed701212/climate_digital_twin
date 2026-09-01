"""Unit tests for risk/engine/risk_engine.py — extended for full coverage."""

from __future__ import annotations

from unittest.mock import patch

import yaml


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


class TestRiskEngine:
    def test_init_missing_config_keys(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump({"heat": {}, "flood": {}, "drought": {}}))
        with patch("risk.engine.risk_engine.logger") as mock_log:
            RiskEngine(str(cfg))
            mock_log.warning.assert_any_call("Missing config key: %s \u2014 using defaults", "risk")
            mock_log.warning.assert_any_call(
                "Missing config key: %s \u2014 using defaults", "composite"
            )
            mock_log.warning.assert_any_call("Missing config key: %s \u2014 using defaults", "shap")
            mock_log.warning.assert_any_call(
                "Missing config key: %s \u2014 using defaults", "output"
            )
            mock_log.warning.assert_any_call("Missing config key: %s \u2014 using defaults", "shap")

    def test_assess_agriculture_risk_no_features(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        assert engine.assess_agriculture_risk("loc-001", None) is None
        assert engine.assess_agriculture_risk("loc-001", {}) is None

    def test_assess_agriculture_risk_with_features(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        # Exercise the real path: vegetative sensitivity is 1.0 and no
        # numeric features are given, so the raw score is exactly 50 -> 0.5.
        # (Mocking _run_coroutine_sync would leak its never-awaited
        # coroutine argument.)
        result = engine.assess_agriculture_risk("loc-001", {"crop_stage": "vegetative"})
        assert result is not None
        assert result.score == 0.5

    def test_assess_all_with_agriculture(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        report = engine.assess_all(
            location_id="loc-001",
            district="Test",
            max_temp=35.0,
            min_temp=22.0,
            rainfall=80.0,
            agriculture_features={"crop_stage": "flowering"},
        )
        assert report.location_id == "loc-001"

    def test_assess_all_without_agriculture(self, tmp_path):
        from risk.engine.risk_engine import RiskEngine

        cfg = tmp_path / "risk.yaml"
        cfg.write_text(yaml.dump(_make_config()))
        engine = RiskEngine(str(cfg))
        report = engine.assess_all(
            location_id="loc-001",
            district="Test",
            max_temp=35.0,
            min_temp=22.0,
            rainfall=80.0,
        )
        assert report.agriculture_risk is None
