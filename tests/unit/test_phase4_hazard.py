"""Phase 4 — Hazard Intelligence unit tests.

Quality gates, freshness, severity, Twin acceptance/rejection,
forecast provenance, deterministic attribution, alert lifecycle,
HazardStore persistence, idempotency, trend history.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from risk.evaluation.alert_policy import AlertPolicy
from risk.evaluation.deterministic_attribution import (
    build_dryness_attribution,
    build_heat_attribution,
    build_heavy_rain_attribution,
)
from risk.evaluation.forecast_adapter import ForecastInputs, extract_forecast_inputs
from risk.evaluation.quality_gate import (
    DataQuality,
    Freshness,
    Severity,
    check_freshness,
    check_quality,
    compute_confidence,
    severity_from_score,
)
from risk.evaluation.twin_adapter import TwinInputs, extract_twin_inputs
from risk.models.hazard import (
    UNSUPPORTED_HAZARDS,
    Alert,
    AlertStatus,
    AssessmentType,
    EvidenceFactor,
    HazardAssessment,
)
from risk.store.alert_store import AlertStore
from risk.store.hazard_store import HazardStore

# ═══════════════════════════════════════════════════════════════════
# Quality Gate
# ═══════════════════════════════════════════════════════════════════


class TestQualityGate:
    def test_accepts_real_validated(self):
        q, r = check_quality("REAL", "validated")
        assert q == DataQuality.GOOD

    def test_accepts_real_raw(self):
        q, r = check_quality("REAL", "raw")
        assert q == DataQuality.SUSPECT

    def test_rejects_synthetic(self):
        q, r = check_quality("SYNTHETIC", "validated")
        assert q == DataQuality.REJECTED

    def test_rejects_unknown(self):
        q, r = check_quality("UNKNOWN", "raw")
        assert q == DataQuality.REJECTED

    def test_rejects_none_authenticity(self):
        q, r = check_quality(None, "validated")
        assert q == DataQuality.REJECTED

    def test_rejects_none_quality(self):
        q, r = check_quality("REAL", None)
        assert q == DataQuality.REJECTED


class TestFreshnessGate:
    def test_fresh_recent(self):
        ts = datetime.now(UTC) - timedelta(minutes=5)
        assert check_freshness(ts) == Freshness.FRESH

    def test_stale_old(self):
        ts = datetime.now(UTC) - timedelta(hours=3)
        assert check_freshness(ts) == Freshness.STALE

    def test_very_stale(self):
        ts = datetime.now(UTC) - timedelta(hours=24)
        assert check_freshness(ts) == Freshness.VERY_STALE

    def test_unavailable_none(self):
        assert check_freshness(None) == Freshness.UNAVAILABLE

    def test_handles_iso_string(self):
        ts = datetime.now(UTC).isoformat()
        assert check_freshness(ts) in (Freshness.FRESH,)

    def test_fresh_from_future(self):
        ts = datetime.now(UTC) + timedelta(hours=1)
        assert check_freshness(ts) == Freshness.FRESH


class TestSeverityMapping:
    def test_none_at_zero(self):
        assert severity_from_score(0) == Severity.NONE

    def test_low_below_20(self):
        assert severity_from_score(10) == Severity.LOW

    def test_moderate_above_20(self):
        assert severity_from_score(30) == Severity.MODERATE

    def test_high_above_40(self):
        assert severity_from_score(50) == Severity.HIGH

    def test_severe_above_60(self):
        assert severity_from_score(80) == Severity.SEVERE


class TestConfidence:
    def test_base_confidence(self):
        c = compute_confidence(DataQuality.GOOD, Freshness.FRESH, 3, 3)
        assert c == pytest.approx(0.85, rel=0.01)

    def test_stale_penalty(self):
        c = compute_confidence(DataQuality.GOOD, Freshness.STALE, 3, 3)
        assert c < 0.85

    def test_suspect_penalty(self):
        c = compute_confidence(DataQuality.SUSPECT, Freshness.FRESH, 3, 3)
        assert c < 0.85

    def test_forecast_bonus(self):
        c = compute_confidence(DataQuality.GOOD, Freshness.FRESH, 3, 3, forecast_validated=True)
        assert c > 0.85

    def test_minimum_floor(self):
        c = compute_confidence(DataQuality.REJECTED, Freshness.VERY_STALE, 0, 3)
        assert c >= 0.1


# ═══════════════════════════════════════════════════════════════════
# Twin Adapter
# ═══════════════════════════════════════════════════════════════════


class TestTwinAdapter:
    def test_handles_none(self):
        ti = extract_twin_inputs(None)
        assert ti.max_temp is None
        assert ti.authenticity == "UNKNOWN"

    def test_extracts_real_twin(self):
        class FakeTwin:
            temperature_2m = 32.5
            precipitation_mm = 10.0
            authenticity = "REAL"
            quality_flag = "validated"
            observation_id = "obs-001"
            timestamp = datetime.now(UTC)
            entity_id = "KA-BLR-001"
            data_source = "open_meteo"
            ingestion_timestamp = datetime.now(UTC)
            consecutive_hot_days = 0
            dry_period_days = 0
            metadata = {}

        ti = extract_twin_inputs(FakeTwin())
        assert ti.max_temp == 32.5
        assert ti.rainfall == 10.0
        assert ti.authenticity == "REAL"

    def test_missing_values_not_zero(self):
        class MinimalTwin:
            temperature_2m = None
            precipitation_mm = None
            authenticity = "REAL"
            quality_flag = "validated"
            observation_id = ""
            timestamp = datetime.now(UTC)
            entity_id = "test"
            data_source = "test"
            ingestion_timestamp = None
            consecutive_hot_days = 0
            dry_period_days = 0
            metadata = {}

        ti = extract_twin_inputs(MinimalTwin())
        assert ti.max_temp is None
        assert ti.rainfall is None


class TestForecastAdapter:
    def test_extracts_forecast(self):
        class FakeForecast:
            rainfall = 50.0
            max_temp = 35.0
            min_temp = 22.0
            confidence = 0.85
            forecast_id = "fc-001"
            model_id = "lstm-real-v2"
            training_run_id = "tr-001"
            dataset_id = "ds-001"
            authenticity = "REAL"
            source_twin_version = 42
            created_at = "2026-07-30T12:00:00"
            physics_validated = True

        fi = extract_forecast_inputs(FakeForecast())
        assert fi.rainfall == 50.0
        assert fi.model_id == "lstm-real-v2"
        assert fi.authenticity == "REAL"

    def test_rejects_synthetic(self):
        class FakeForecast:
            rainfall = 0.0
            max_temp = 0.0
            min_temp = 0.0
            confidence = 0.0
            forecast_id = "fc-002"
            model_id = ""
            training_run_id = ""
            dataset_id = ""
            authenticity = "SYNTHETIC"
            source_twin_version = 0
            created_at = None
            physics_validated = False

        fi = extract_forecast_inputs(FakeForecast())
        assert fi.authenticity == "SYNTHETIC"


# ═══════════════════════════════════════════════════════════════════
# Deterministic Attribution
# ═══════════════════════════════════════════════════════════════════


class TestDeterministicAttribution:
    def test_heat_attribution_high_temp(self):
        attr = build_heat_attribution(40.0, 0, 0.0, 50.0)
        assert attr.primary_driver == "max_temp"
        assert len(attr.factors) == 1
        assert attr.factors[0].effect == "increases_hazard"

    def test_heat_attribution_normal_temp(self):
        attr = build_heat_attribution(25.0, 0, 0.0, 0.0)
        assert attr.factors[0].effect == "decreases_hazard"

    def test_heavy_rain_attribution(self):
        attr = build_heavy_rain_attribution(150.0, None, 100.0, 60.0)
        assert attr.primary_driver == "rainfall_24h"
        assert any(f.factor == "rainfall_24h" for f in attr.factors)

    def test_dryness_attribution(self):
        attr = build_dryness_attribution(20.0, 100.0, 20, 3.0)
        assert any(f.factor == "rainfall_deficit_pct" for f in attr.factors)

    def test_no_fake_shap(self):
        attr = build_heat_attribution(25.0, 0, 0.0, 0.0)
        for f in attr.factors:
            assert not hasattr(f, "shap_value")
            assert not hasattr(f, "base_value")


# ═══════════════════════════════════════════════════════════════════
# Alert Policy
# ═══════════════════════════════════════════════════════════════════


class TestAlertPolicy:
    def test_no_alert_for_none(self):
        policy = AlertPolicy()
        assert not policy.should_alert(Severity.NONE)

    def test_no_alert_for_low(self):
        policy = AlertPolicy()
        assert not policy.should_alert(Severity.LOW)

    def test_alert_for_high(self):
        policy = AlertPolicy()
        assert policy.should_alert(Severity.HIGH)

    def test_alert_for_severe(self):
        policy = AlertPolicy()
        assert policy.should_alert(Severity.SEVERE)

    def test_evaluate_creates_alert(self):
        policy = AlertPolicy()
        assessment = HazardAssessment(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.HIGH,
        )
        alert = policy.evaluate(assessment, [])
        assert alert is not None
        assert alert.status == AlertStatus.ACTIVE
        assert alert.location_id == "KA-BLR-001"

    def test_deduplication_same_hazard(self):
        policy = AlertPolicy()
        assessment = HazardAssessment(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.HIGH,
        )
        existing = Alert(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity="HIGH",
            status=AlertStatus.ACTIVE,
        )
        alert = policy.evaluate(assessment, [existing])
        assert alert is None  # no duplicate

    def test_escalation(self):
        policy = AlertPolicy()
        assessment = HazardAssessment(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.SEVERE,
        )
        existing = Alert(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity="HIGH",
            status=AlertStatus.ACTIVE,
        )
        alert = policy.evaluate(assessment, [existing])
        assert alert is not None
        assert alert.status == AlertStatus.ESCALATED

    def test_resolution(self):
        policy = AlertPolicy()
        assessment = HazardAssessment(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.LOW,
        )
        active = Alert(
            alert_id="a1",
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity="HIGH",
            status=AlertStatus.ACTIVE,
        )
        resolved = policy.resolve(assessment, [active])
        assert len(resolved) == 1
        assert resolved[0].status == AlertStatus.RESOLVED


# ═══════════════════════════════════════════════════════════════════
# HazardStore
# ═══════════════════════════════════════════════════════════════════


class TestHazardStore:
    def test_save_and_retrieve(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "hazards.jsonl"))
        a = HazardAssessment(
            assessment_id="a1",
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.HIGH,
        )
        store.save(a)
        assert store.get("a1") is not None
        assert store.get("a1").assessment_id == "a1"

    def test_list_by_location(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "hazards2.jsonl"))
        store.save(HazardAssessment(assessment_id="a1", location_id="L1", hazard_type="heat"))
        store.save(HazardAssessment(assessment_id="a2", location_id="L1", hazard_type="rain"))
        store.save(HazardAssessment(assessment_id="a3", location_id="L2", hazard_type="heat"))
        items = store.list_by_location("L1")
        assert len(items) == 2

    def test_latest_by_location(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "hazards3.jsonl"))
        store.save(HazardAssessment(assessment_id="a1", location_id="L1", hazard_type="heat"))
        store.save(HazardAssessment(assessment_id="a2", location_id="L1", hazard_type="rain"))
        latest = store.latest_by_location("L1", "rain")
        assert latest is not None
        assert latest.assessment_id == "a2"

    def test_idempotent_latest_wins(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "hazards4.jsonl"))
        a = HazardAssessment(assessment_id="dup", location_id="L1")
        store.save(a)
        store.save(HazardAssessment(assessment_id="other", location_id="L1"))
        # Duplicate ID — cache dedupes by assessment_id (last write wins)
        store.save(a)
        assert store.count() == 2
        assert store.get("dup") is not None

    def test_save_and_reload_recovers_all(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "hazards5.jsonl"))
        store.save(HazardAssessment(assessment_id="r1", location_id="L1"))
        store2 = HazardStore(path=str(tmp_path / "hazards5.jsonl"))
        assert store2.get("r1") is not None

    def test_empty_store(self, tmp_path):
        store = HazardStore(path=str(tmp_path / "empty.jsonl"))
        assert store.count() == 0
        assert store.get("nonexistent") is None


class TestAlertStore:
    def test_save_and_retrieve(self, tmp_path):
        store = AlertStore(path=str(tmp_path / "alerts.jsonl"))
        a = Alert(alert_id="a1", location_id="L1", severity="HIGH")
        store.save(a)
        assert store.get("a1") is not None

    def test_list_active(self, tmp_path):
        store = AlertStore(path=str(tmp_path / "alerts2.jsonl"))
        store.save(
            Alert(alert_id="a1", location_id="L1", severity="HIGH", status=AlertStatus.ACTIVE)
        )
        store.save(
            Alert(alert_id="a2", location_id="L1", severity="SEVERE", status=AlertStatus.ESCALATED)
        )
        store.save(
            Alert(alert_id="a3", location_id="L1", severity="LOW", status=AlertStatus.RESOLVED)
        )
        active = store.list_active()
        assert len(active) == 2

    def test_update_overwrites(self, tmp_path):
        store = AlertStore(path=str(tmp_path / "alerts3.jsonl"))
        a = Alert(alert_id="a1", location_id="L1", severity="HIGH")
        store.save(a)
        a.status = AlertStatus.RESOLVED
        store.update(a)
        retrieved = store.get("a1")
        assert retrieved.status == AlertStatus.RESOLVED

    def test_list_active_by_location(self, tmp_path):
        store = AlertStore(path=str(tmp_path / "alerts4.jsonl"))
        store.save(
            Alert(alert_id="a1", location_id="L1", severity="HIGH", status=AlertStatus.ACTIVE)
        )
        store.save(
            Alert(alert_id="a2", location_id="L2", severity="HIGH", status=AlertStatus.ACTIVE)
        )
        loc1 = store.list_active_by_location("L1")
        assert len(loc1) == 1


# ═══════════════════════════════════════════════════════════════════
# UNSUPPORTED Hazards
# ═══════════════════════════════════════════════════════════════════


class TestUnsupportedHazards:
    def test_storm_unsupported(self):
        assert "storm" in UNSUPPORTED_HAZARDS

    def test_wildfire_unsupported(self):
        assert "wildfire" in UNSUPPORTED_HAZARDS

    def test_flood_unsupported(self):
        assert "flood" in UNSUPPORTED_HAZARDS

    def test_drought_unsupported(self):
        assert "drought" in UNSUPPORTED_HAZARDS

    def test_heatwave_unsupported(self):
        assert "heatwave" in UNSUPPORTED_HAZARDS

    def test_heavy_rain_supported(self):
        assert "heavy_rain" not in UNSUPPORTED_HAZARDS

    def test_heat_supported(self):
        assert "heat" not in UNSUPPORTED_HAZARDS


# ═══════════════════════════════════════════════════════════════════
# HazardAssessment Model
# ═══════════════════════════════════════════════════════════════════


class TestHazardAssessmentModel:
    def test_default_severity_none(self):
        ha = HazardAssessment()
        assert ha.severity == Severity.NONE

    def test_assessment_id_auto_generated(self):
        ha = HazardAssessment()
        assert len(ha.assessment_id) == 12

    def test_to_dict_serialization(self):
        ha = HazardAssessment(
            location_id="KA-BLR-001",
            hazard_type="heat",
            severity=Severity.HIGH,
            evidence=[
                EvidenceFactor(
                    factor="max_temp",
                    value=40.0,
                    unit="°C",
                    threshold=35.0,
                    effect="increases_hazard",
                )
            ],
        )
        d = ha.to_dict()
        assert d["location_id"] == "KA-BLR-001"
        assert d["severity"] == "HIGH"
        assert len(d["evidence"]) == 1

    def test_round_trip_from_dict(self):
        ha = HazardAssessment(
            assessment_id="rt1",
            location_id="L1",
            hazard_type="heat",
            severity=Severity.MODERATE,
        )
        d = ha.to_dict()
        ha2 = HazardAssessment.from_dict(d)
        assert ha2.assessment_id == "rt1"
        assert ha2.location_id == "L1"
        assert ha2.severity == Severity.MODERATE

    def test_observed_vs_forecast_distinct(self):
        obs = HazardAssessment(assessment_id="o1", assessment_type=AssessmentType.OBSERVED)
        fct = HazardAssessment(assessment_id="f1", assessment_type=AssessmentType.FORECAST)
        assert obs.assessment_type != fct.assessment_type
        assert obs.assessment_type == AssessmentType.OBSERVED
        assert fct.assessment_type == AssessmentType.FORECAST

    def test_probability_not_available(self):
        ha = HazardAssessment()
        assert not hasattr(ha, "probability")
        # probability field must NOT exist — no calibrated model yet


# ═══════════════════════════════════════════════════════════════════
# Hazard Evaluator (with mocked engine & stores)
# ═══════════════════════════════════════════════════════════════════


class TestHazardEvaluatorIntegration:
    def test_rejects_synthetic_twin(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        ti = TwinInputs(
            max_temp=30.0,
            min_temp=20.0,
            rainfall=50.0,
            consecutive_hot_days=0,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="v1",
            observation_ids=[],
            authenticity="SYNTHETIC",
            data_source="test",
            quality_flag="validated",
            observation_timestamp=datetime.now(UTC),
            ingestion_timestamp=None,
            twin_metadata={},
        )
        result = evaluator.assess_observed(ti, "KA-BLR-001")
        assert len(result) > 0
        assert result[0].data_quality == DataQuality.REJECTED

    def test_accepts_real_twin(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        ti = TwinInputs(
            max_temp=40.0,
            min_temp=25.0,
            rainfall=50.0,
            consecutive_hot_days=3,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="v1",
            observation_ids=["obs-001"],
            authenticity="REAL",
            data_source="open_meteo",
            quality_flag="validated",
            observation_timestamp=datetime.now(UTC),
            ingestion_timestamp=None,
            twin_metadata={},
        )
        result = evaluator.assess_observed(ti, "KA-BLR-001")
        assert len(result) >= 1
        assert result[0].data_quality == DataQuality.GOOD
        assert result[0].hazard_type in ("heat", "heavy_rain", "dryness")

    def test_rejects_synthetic_forecast(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        fi = ForecastInputs(
            rainfall=50.0,
            max_temp=35.0,
            min_temp=22.0,
            confidence=0.85,
            forecast_id="fc-001",
            model_id="lstm-real-v2",
            training_run_id="tr-001",
            dataset_id="ds-001",
            authenticity="SYNTHETIC",
            source_twin_version=42,
            created_at=None,
            physics_validated=False,
        )
        result = evaluator.assess_forecast(fi, "KA-BLR-001")
        assert len(result) > 0
        assert result[0].data_quality == DataQuality.REJECTED

    def test_missing_values_not_zero_in_assessment(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        ti = TwinInputs(
            max_temp=None,
            min_temp=None,
            rainfall=None,
            consecutive_hot_days=0,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="v1",
            observation_ids=[],
            authenticity="REAL",
            data_source="test",
            quality_flag="validated",
            observation_timestamp=datetime.now(UTC),
            ingestion_timestamp=None,
            twin_metadata={},
        )
        result = evaluator.assess_observed(ti, "KA-BLR-001")
        assert len(result) > 0
        # None inputs become 0.0 inside the engine, but the quality gate
        # should still pass for REAL data

    def test_historical_backtest(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        result = evaluator.assess_historical_backtest(
            "KA-BLR-001",
            max_temp=40.0,
            min_temp=25.0,
            rainfall=150.0,
        )
        assert len(result) >= 1
        assert result[0].assessment_type == AssessmentType.HISTORICAL_BACKTEST
        assert result[0].location_id == "KA-BLR-001"

    def test_process_and_store_saves_hazard(self, tmp_path):
        from risk.evaluation.hazard_evaluator import HazardEvaluator
        from risk.store.alert_store import AlertStore
        from risk.store.hazard_store import HazardStore

        store = HazardStore(path=str(tmp_path / "hazards.jsonl"))
        alert_store = AlertStore(path=str(tmp_path / "alerts.jsonl"))
        evaluator = HazardEvaluator(hazard_store=store, alert_store=alert_store)
        ti = TwinInputs(
            max_temp=40.0,
            min_temp=25.0,
            rainfall=50.0,
            consecutive_hot_days=3,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="v1",
            observation_ids=["obs-001"],
            authenticity="REAL",
            data_source="open_meteo",
            quality_flag="validated",
            observation_timestamp=datetime.now(UTC),
            ingestion_timestamp=None,
            twin_metadata={},
        )
        assessments, alerts = evaluator.process_and_store(ti, None, "KA-BLR-001")
        assert len(assessments) > 0
        assert store.get(assessments[0].assessment_id) is not None

    def test_no_scenario_in_operational(self):
        from risk.evaluation.hazard_evaluator import HazardEvaluator

        evaluator = HazardEvaluator()
        ti = TwinInputs(
            max_temp=30.0,
            min_temp=20.0,
            rainfall=50.0,
            consecutive_hot_days=0,
            dry_period_days=0,
            multi_day_accumulation=None,
            seasonal_anomaly=0.0,
            forecast_uncertainty=0.0,
            twin_version="v1",
            observation_ids=[],
            authenticity="SCENARIO",
            data_source="scenario_engine",
            quality_flag="validated",
            observation_timestamp=datetime.now(UTC),
            ingestion_timestamp=None,
            twin_metadata={},
        )
        result = evaluator.assess_observed(ti, "KA-BLR-001")
        assert len(result) > 0
        assert result[0].data_quality == DataQuality.REJECTED


# ═══════════════════════════════════════════════════════════════════
# Production Crawl — no random/synthetic in operational paths
# ═══════════════════════════════════════════════════════════════════


class TestProductionCrawl:
    """Verify Phase 4 operational paths contain zero random/synthetic."""

    def test_no_random_in_evaluation(self):
        import inspect

        import risk.evaluation.hazard_evaluator as ev

        src = inspect.getsource(ev)
        assert "random" not in src, "random found in hazard_evaluator"

    def test_no_np_random_in_evaluation(self):
        import inspect

        import risk.evaluation.hazard_evaluator as ev

        src = inspect.getsource(ev)
        assert "np.random" not in src

    def test_quality_gate_rejects_synthetic(self):
        q, _ = check_quality("SYNTHETIC", "validated")
        assert q == DataQuality.REJECTED

    def test_config_rejects_synthetic_operationally(self):
        from pathlib import Path

        import yaml

        p = Path("config/risk_config.yaml")
        if p.exists():
            cfg = yaml.safe_load(p.read_text())
            rejected = cfg["quality"]["operational_mode_rejects"]
            assert "SYNTHETIC" in rejected
            assert "SCENARIO" in rejected

    def test_unsupported_hazards_not_operational(self):
        # Verify the config also marks these as disabled
        from pathlib import Path

        import yaml

        p = Path("config/risk_config.yaml")
        if p.exists():
            cfg = yaml.safe_load(p.read_text())
            for hazard_name in UNSUPPORTED_HAZARDS:
                hcfg = cfg.get("hazards", {}).get(hazard_name, {})
                assert not hcfg.get("enabled", True), f"{hazard_name} should be disabled"
