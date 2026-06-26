"""Unit tests for the RiskAPI contract."""

import pytest


class TestRiskAPIContract:
    """Test that RiskAPI contract can be implemented."""

    def test_contract_has_required_methods(self):
        from risk.api.contract import RiskAPI

        methods = [
            "calculate_risk",
            "calculate_heat_risk",
            "calculate_flood_risk",
            "calculate_drought_risk",
            "generate_explanation",
            "generate_report",
            "export_results",
        ]
        for method in methods:
            assert hasattr(RiskAPI, method)
            assert callable(getattr(RiskAPI, method))

    def test_contract_is_abstract(self):
        from risk.api.contract import RiskAPI

        with pytest.raises(TypeError):
            RiskAPI()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        from risk.api.contract import RiskAPI

        class TestImpl(RiskAPI):
            def calculate_risk(self, location_id, _district, _max_temp, _min_temp, _rainfall, **_kwargs):
                return {"location_id": location_id, "score": 50.0}

            def calculate_heat_risk(self, _max_temp, _consecutive_hot_days=0, _seasonal_anomaly=0.0):
                return {"score": 50.0}

            def calculate_flood_risk(self, _rainfall, _multi_day_accumulation=None, _forecast_uncertainty=0.0):
                return {"score": 30.0}

            def calculate_drought_risk(self, _rainfall, _historical_mean_rainfall=100.0, _max_temp=30.0, _historical_mean_temp=28.0, _dry_period_days=0):
                return {"score": 20.0}

            def generate_explanation(self, prediction, feature_values, _prediction_confidence=0.0):
                return {"prediction": prediction, "features": feature_values}

            def generate_report(self, location_id, _district, _report, _formats=None):
                return {"json": f"output/{location_id}_report.json"}

            def export_results(self, _location_id, _report, _output_format="json"):
                return '{"score": 50}'

        impl = TestImpl()
        result = impl.calculate_risk("KA-BLR-001", "Bangalore", 38.0, 20.0, 80.0)
        assert result["location_id"] == "KA-BLR-001"
        assert result["score"] == 50.0
