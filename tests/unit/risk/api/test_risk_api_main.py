"""Tests for risk API routes and lifespan."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from risk.api.main import _get_engine, app, lifespan
from risk.models.risk_models import (
    CompositeRiskScore,
    DroughtRiskScore,
    FloodRiskScore,
    HeatRiskScore,
    RiskReport,
)


class TestLifespan:
    def test_lifespan_startup_shutdown(self):
        mock_engine = MagicMock()
        with patch("risk.api.main.RiskEngine", return_value=mock_engine):
            import risk.api.main as m

            async def run():
                async with lifespan(app):
                    assert m._engine is mock_engine
                assert m._engine is None

            asyncio.run(run())

    def test_lifespan_logs_startup(self, caplog):
        caplog.set_level(20)
        with patch("risk.api.main.RiskEngine", return_value=MagicMock()):

            async def run():
                async with lifespan(app):
                    pass

            asyncio.run(run())
        assert "RiskEngine initialized" in caplog.text


class TestGetEngine:
    def test_get_engine_returns_instance(self):
        import risk.api.main as m

        mock_engine = MagicMock()
        try:
            m._engine = mock_engine
            assert _get_engine() is mock_engine
        finally:
            m._engine = None

    def test_get_engine_raises_when_none(self):
        import risk.api.main as m

        m._engine = None
        with pytest.raises(RuntimeError, match="Engine not initialized"):
            _get_engine()


@pytest.fixture
def mock_risk_engine():
    eng = MagicMock()
    eng.assess_heat_risk.return_value = HeatRiskScore(
        score=45.0,
        max_temperature_contribution=20.0,
        consecutive_hot_days_contribution=15.0,
        seasonal_anomaly_contribution=10.0,
        consecutive_hot_days=3,
        seasonal_anomaly=2.0,
    )
    eng.assess_flood_risk.return_value = FloodRiskScore(
        score=30.0,
        rainfall_intensity_contribution=10.0,
        multi_day_accumulation_contribution=10.0,
        forecast_uncertainty_contribution=10.0,
        multi_day_accumulation=80.0,
        rainfall_intensity=40.0,
    )
    eng.assess_drought_risk.return_value = DroughtRiskScore(
        score=25.0,
        rainfall_deficit_contribution=10.0,
        temperature_increase_contribution=8.0,
        dry_period_days_contribution=7.0,
        rainfall_deficit_percent=-15.0,
        temperature_anomaly=1.5,
    )
    eng.assess_composite_risk.return_value = CompositeRiskScore(
        score=35.0,
        heat_score=45.0,
        flood_score=30.0,
        drought_score=25.0,
        weights={},
    )
    report = RiskReport(
        location_id="loc-001",
        district="Test",
        heat_risk=eng.assess_heat_risk.return_value,
        flood_risk=eng.assess_flood_risk.return_value,
        drought_risk=eng.assess_drought_risk.return_value,
        composite_risk=eng.assess_composite_risk.return_value,
    )
    eng.assess_all.return_value = report
    eng.generate_full_report.return_value = {"json": "/tmp/report.json"}
    return eng


@pytest.fixture
def client(mock_risk_engine):
    import risk.api.main as m

    m._engine = mock_risk_engine
    yield TestClient(app)
    m._engine = None


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestAssessEndpoint:
    def test_assess_risk(self, client):
        resp = client.post("/risk/assess", json={"location_id": "loc-001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["location_id"] == "loc-001"

    def test_assess_heat(self, client):
        resp = client.post("/risk/heat", json={"location_id": "loc-001", "max_temp": 38.0})
        assert resp.status_code == 200
        assert resp.json()["score"] == 45.0

    def test_assess_flood(self, client):
        resp = client.post("/risk/flood", json={"location_id": "loc-001", "rainfall": 120.0})
        assert resp.status_code == 200
        assert resp.json()["score"] == 30.0

    def test_assess_drought(self, client):
        resp = client.post("/risk/drought", json={"location_id": "loc-001", "rainfall": 50.0})
        assert resp.status_code == 200
        assert resp.json()["score"] == 25.0

    def test_assess_composite(self, client):
        resp = client.post("/risk/composite", json={"score": 50.0})
        assert resp.status_code == 200
        assert resp.json()["score"] == 35.0

    def test_assess_report(self, client):
        resp = client.post("/risk/report", json={"location_id": "loc-001"})
        assert resp.status_code == 200
        assert resp.json()["report"]["location_id"] == "loc-001"
        assert "outputs" in resp.json()
