"""Phase 6 production-integrity tests.

Gate: no fabricated/random/synthetic forecast values may reach the gateway,
and the dashboard/copilot must never present observations as forecasts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REAL_DATA_DIR = Path("data/real")


# ---------------------------------------------------------------------------
# Model registry: REAL + VALIDATED is the only production choice
# ---------------------------------------------------------------------------
class TestRegistryProductionGate:
    def test_get_best_require_real_validated_returns_real_model(self) -> None:
        from models.registry import ModelRegistry

        best = ModelRegistry().get_best(
            metric="rmse", ascending=True, require_validated=True, require_real=True
        )
        assert best["authenticity"] == "REAL"
        assert best["status"] == "VALIDATED"
        assert best["name"] == "lstm-real-v2"

    def test_legacy_synthetic_models_never_win_real_gate(self) -> None:
        from models.registry import ModelRegistry

        best = ModelRegistry().get_best(
            metric="rmse", ascending=True, require_validated=True, require_real=True
        )
        for m in ["baseline", "lstm", "transformer"]:
            assert best["name"] != m

    def test_get_best_real_gate_raises_when_none(self, tmp_path) -> None:
        from models.registry import ModelRegistry

        reg = ModelRegistry(registry_path=str(tmp_path / "metadata.json"))
        reg.register(
            name="fake-synth",
            architecture="lstm",
            checkpoint_path="models/checkpoints/fake.pt",
            status="VALIDATED",
            authenticity="SYNTHETIC",
            metrics={"rmse": 1.0},
        )
        with pytest.raises(KeyError):
            reg.get_best(metric="rmse", require_real=True, require_validated=True)


# ---------------------------------------------------------------------------
# Forecast pipeline: raises instead of fabricating
# ---------------------------------------------------------------------------
class TestPipelineNoFabrication:
    def _pipeline(self, registry):
        from climatedt.pipeline.forecast_pipeline import ForecastPipeline

        return ForecastPipeline(
            feature_engine=MagicMock(),
            model_registry=registry,
            observation_store=MagicMock(),
            forecast_store=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_predict_raises_model_unavailable_when_no_real_model(self, tmp_path) -> None:
        from climatedt.pipeline.forecast_pipeline import ForecastUnavailableError
        from models.registry import ModelRegistry

        reg = ModelRegistry(registry_path=str(tmp_path / "metadata.json"))
        reg.register(
            name="fake-synth",
            architecture="lstm",
            checkpoint_path="models/checkpoints/fake.pt",
            status="VALIDATED",
            authenticity="SYNTHETIC",
            metrics={"rmse": 1.0},
        )
        pipeline = self._pipeline(reg)
        with pytest.raises(ForecastUnavailableError) as excinfo:
            await pipeline.predict_with_best("KA-BLR-001", "temperature_2m", 24)
        assert excinfo.value.code == "MODEL_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_retrain_raises_not_supported(self) -> None:
        from climatedt.pipeline.forecast_pipeline import ForecastUnavailableError

        pipeline = self._pipeline(MagicMock())
        with pytest.raises(ForecastUnavailableError) as excinfo:
            await pipeline.train_forecast_model("xgboost")
        assert excinfo.value.code == "NOT_SUPPORTED"


# ---------------------------------------------------------------------------
# Gateway contract: 503 with structured error, never fabricated data
# ---------------------------------------------------------------------------
class TestForecastUnavailableContract:
    def _client_with_unavailable(self, error_code: str, message: str):
        import backend.api.main as api_main
        from climatedt.pipeline.forecast_pipeline import ForecastUnavailableError
        from fastapi.routing import APIRoute
        from fastapi.testclient import TestClient

        async def fail(location_id="", target_variable="", horizon=24):
            raise ForecastUnavailableError(error_code, message)

        async def fail_retrain(model_type="xgboost", target_variable="temperature_2m"):
            raise ForecastUnavailableError(error_code, message)

        app = api_main.create_app()
        forecast_route = next(
            r for r in app.routes if isinstance(r, APIRoute) and r.path == "/forecast/predict"
        )
        dep_callable = next(
            d.call
            for d in forecast_route.dependant.dependencies
            if d.call is not None and d.call.__name__ == "get_forecast_pipeline"
        )
        app.dependency_overrides[dep_callable] = lambda: MagicMock(
            predict_with_best=fail, train_forecast_model=fail_retrain
        )
        return TestClient(app)

    def test_predict_returns_503_with_error_code(self) -> None:
        client = self._client_with_unavailable("MODEL_UNAVAILABLE", "No REAL + VALIDATED model")
        resp = client.post(
            "/forecast/predict",
            json={
                "location_id": "KA-BLR-001",
                "target_variable": "temperature_2m",
                "horizon_hours": 24,
            },
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error_code"] == "MODEL_UNAVAILABLE"
        assert "No REAL + VALIDATED model" in body["detail"]["message"]

    def test_retrain_returns_501(self) -> None:
        client = self._client_with_unavailable(
            "NOT_SUPPORTED", "Retraining is not a production path"
        )
        resp = client.post("/forecast/retrain", params={"model_type": "xgboost"})
        assert resp.status_code == 501
        assert resp.json()["detail"]["error_code"] == "NOT_SUPPORTED"


# ---------------------------------------------------------------------------
# Real data manifest: production input is verified, not assumed
# ---------------------------------------------------------------------------
class TestRealDataManifest:
    def test_real_data_manifest_verifies(self) -> None:
        manifest_path = REAL_DATA_DIR / "dataset_manifest.json"
        assert manifest_path.exists(), "data/real/dataset_manifest.json missing"
        manifest = json.loads(manifest_path.read_text())
        assert "checksums" in manifest and manifest["checksums"]
        for fname, expected_cs in manifest["checksums"].items():
            f = REAL_DATA_DIR / fname
            assert f.exists(), f"manifest-listed file missing: {fname}"
            actual_cs = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            assert actual_cs == expected_cs, f"checksum mismatch for {fname}"

    def test_real_testing_split_present(self) -> None:
        assert (REAL_DATA_DIR / "testing.csv").exists()
        assert (REAL_DATA_DIR / "testing.csv").stat().st_size > 0


# ---------------------------------------------------------------------------
# Dashboard: observations never masquerade as forecasts
# ---------------------------------------------------------------------------
class TestDashboardNoObservationAsForecast:
    def test_forecast_failure_returns_empty_not_observations(self) -> None:
        from dashboard.services.api_client import DashboardAPI

        api = DashboardAPI(base_url="http://test/api/v1", timeout=1)
        import requests

        original_post = api._session.post

        def fail(*args, **kwargs):
            raise requests.ConnectionError("no gateway")

        api._session.post = fail  # type: ignore[method-assign]
        try:
            result = api.get_forecast("KA-BLR-001", horizon=3)
        finally:
            api._session.post = original_post
        assert result == []
        assert all(not isinstance(r, dict) or r.get("state_type") != "forecast" for r in result)
