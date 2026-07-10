"""Tests for the AgricultureRiskModel."""

import pytest


class TestAgricultureRiskModel:
    """Test suite for AgricultureRiskModel."""

    @pytest.fixture
    def model(self):
        from risk.models.agriculture_risk import AgricultureRiskModel

        return AgricultureRiskModel()

    @pytest.mark.asyncio
    async def test_assess_returns_riskscore(self, model):
        """Test assess returns a properly structured RiskScore."""
        from risk.models.risk_models import HazardType, RiskCategory

        result = await model.assess(
            location_id="loc-001",
            growing_season_temp=25.0,
            growing_season_precip=100.0,
        )
        assert result.hazard_type == HazardType.DROUGHT
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.category, RiskCategory)
        assert isinstance(result.description, str)

    @pytest.mark.asyncio
    async def test_optimal_conditions(self, model):
        """Test optimal growing conditions give low risk."""
        from risk.models.risk_models import RiskCategory

        result = await model.assess(
            location_id="loc-001",
            growing_season_temp=25.0,
            growing_season_precip=120.0,
            soil_moisture=0.3,
            ndvi=0.7,
            crop_stage="vegetative",
            monsoon_performance=0.8,
        )
        assert result.score < 0.4
        assert result.category in (RiskCategory.LOW, RiskCategory.MODERATE)

    @pytest.mark.asyncio
    async def test_poor_conditions(self, model):
        """Test poor growing conditions give high risk."""
        result = await model.assess(
            location_id="loc-001",
            growing_season_temp=40.0,
            growing_season_precip=5.0,
            precipitation_deficit=60.0,
            temperature_stress_days=15,
            soil_moisture=0.05,
            ndvi=0.1,
            crop_stage="flowering",
            monsoon_performance=0.1,
        )
        assert result.score > 0.5

    @pytest.mark.asyncio
    async def test_frost_conditions(self, model):
        """Test freezing conditions give high risk."""
        result = await model.assess(
            location_id="loc-001",
            growing_season_temp=-5.0,
            growing_season_precip=2.0,
            temperature_stress_days=10,
            ndvi=0.05,
        )
        assert result.score > 0.55

    @pytest.mark.asyncio
    async def test_no_features(self, model):
        """Test with no features returns moderate risk."""
        from risk.models.risk_models import RiskCategory

        result = await model.assess(location_id="loc-001")
        assert 0.0 <= result.score <= 1.0
        assert result.category == RiskCategory.MODERATE

    def test_temperature_stress_score(self, model):
        """Test temperature stress scoring."""
        assert model._temperature_stress_score(25.0) == 0.0
        assert model._temperature_stress_score(-1.0) > 80.0
        assert model._temperature_stress_score(40.0) > 50.0

    def test_precipitation_adequacy_score(self, model):
        """Test precipitation adequacy scoring."""
        assert model._precipitation_adequacy_score(100.0) == 0.0
        assert model._precipitation_adequacy_score(5.0) > 50.0
        assert model._precipitation_adequacy_score(500.0) > 50.0

    @pytest.mark.asyncio
    async def test_crop_stage_sensitivity(self, model):
        """Test different crop stages affect risk."""
        base_features = {
            "growing_season_temp": 38.0,
            "growing_season_precip": 10.0,
        }

        result_fallow = await model.assess(
            location_id="loc-001", **base_features, crop_stage="fallow"
        )
        result_flowering = await model.assess(
            location_id="loc-001", **base_features, crop_stage="flowering"
        )

        assert result_flowering.score >= result_fallow.score

    @pytest.mark.asyncio
    async def test_batch_assess_pattern(self, model):
        """Test multiple assessments can be made."""
        results = []
        for stage in ["planting", "vegetative", "flowering", "grain_fill"]:
            result = await model.assess(
                location_id="loc-001",
                growing_season_temp=35.0,
                growing_season_precip=30.0,
                crop_stage=stage,
            )
            results.append(result)

        assert len(results) == 4
        assert all(0.0 <= r.score <= 1.0 for r in results)
