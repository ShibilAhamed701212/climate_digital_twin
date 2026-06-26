"""Unit tests for risk scoring modules (heat, flood, drought, composite)."""



class TestHeatRiskScoring:
    """Test heat risk scoring calculations."""

    def test_normal_temps_no_risk(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        result = calculate_heat_risk(max_temp=25.0)
        assert result.score == 0.0
        assert result.max_temperature_contribution == 0.0

    def test_high_temp_elevates_risk(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        result = calculate_heat_risk(max_temp=40.0)
        assert result.score > 0.0
        assert result.max_temperature_contribution > 0.0

    def test_consecutive_hot_days_increase_risk(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        base = calculate_heat_risk(max_temp=38.0, consecutive_hot_days=0)
        elevated = calculate_heat_risk(max_temp=38.0, consecutive_hot_days=5)
        assert elevated.score > base.score
        assert elevated.consecutive_hot_days_contribution > base.consecutive_hot_days_contribution

    def test_score_bounded_0_100(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        result = calculate_heat_risk(max_temp=55.0, consecutive_hot_days=30, seasonal_anomaly=10.0)
        assert 0 <= result.score <= 100

    def test_seasonal_anomaly_contribution(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        result = calculate_heat_risk(max_temp=35.0, seasonal_anomaly=3.0)
        assert result.seasonal_anomaly_contribution > 0.0

    def test_custom_threshold(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        result = calculate_heat_risk(max_temp=38.0, hot_day_threshold=40.0)
        assert result.max_temperature_contribution == 0.0

    def test_custom_weights(self):
        from risk.scoring.heat_risk import calculate_heat_risk

        weights = {"max_temperature": 1.0, "consecutive_hot_days": 0.0, "seasonal_anomaly": 0.0}
        result = calculate_heat_risk(max_temp=40.0, consecutive_hot_days=10, weights=weights)
        assert result.max_temperature_contribution > 0.0
        assert result.score == result.max_temperature_contribution


class TestFloodRiskScoring:
    """Test flood risk scoring calculations."""

    def test_no_rain_no_risk(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        result = calculate_flood_risk(rainfall=0.0)
        assert result.score == 0.0

    def test_heavy_rain_elevates_risk(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        result = calculate_flood_risk(rainfall=150.0)
        assert result.score > 0.0
        assert result.rainfall_intensity_contribution > 0.0

    def test_multi_day_accumulation(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        base = calculate_flood_risk(rainfall=50.0)
        accumulated = calculate_flood_risk(rainfall=50.0, multi_day_accumulation=300.0)
        assert accumulated.score > base.score

    def test_forecast_uncertainty_amplifies(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        certain = calculate_flood_risk(rainfall=80.0, forecast_uncertainty=0.0)
        uncertain = calculate_flood_risk(rainfall=80.0, forecast_uncertainty=0.8)
        assert uncertain.score >= certain.score

    def test_score_bounded_0_100(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        result = calculate_flood_risk(rainfall=500.0, multi_day_accumulation=1000.0, forecast_uncertainty=1.0)
        assert 0 <= result.score <= 100

    def test_custom_threshold(self):
        from risk.scoring.flood_risk import calculate_flood_risk

        result = calculate_flood_risk(rainfall=120.0, heavy_rain_threshold=200.0)
        assert result.rainfall_intensity_contribution < 50.0


class TestDroughtRiskScoring:
    """Test drought risk scoring calculations."""

    def test_normal_rainfall_no_risk(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        result = calculate_drought_risk(
            rainfall=100.0,
            historical_mean_rainfall=100.0,
            max_temp=28.0,
            historical_mean_temp=28.0,
        )
        assert result.score == 0.0

    def test_rainfall_deficit_increases_risk(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        result = calculate_drought_risk(
            rainfall=30.0,
            historical_mean_rainfall=100.0,
            max_temp=30.0,
            historical_mean_temp=28.0,
        )
        assert result.score > 0.0
        assert result.rainfall_deficit_percent < -20.0

    def test_dry_period_increases_risk(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        base = calculate_drought_risk(rainfall=50.0, historical_mean_rainfall=100.0, dry_period_days=0)
        extended = calculate_drought_risk(rainfall=50.0, historical_mean_rainfall=100.0, dry_period_days=20)
        assert extended.score > base.score

    def test_score_bounded_0_100(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        result = calculate_drought_risk(
            rainfall=0.0,
            historical_mean_rainfall=100.0,
            max_temp=45.0,
            historical_mean_temp=28.0,
            dry_period_days=60,
        )
        assert 0 <= result.score <= 100

    def test_temperature_anomaly_contribution(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        result = calculate_drought_risk(
            rainfall=80.0,
            historical_mean_rainfall=100.0,
            max_temp=38.0,
            historical_mean_temp=28.0,
        )
        assert result.temperature_anomaly > 0.0

    def test_surplus_rainfall_no_deficit_risk(self):
        from risk.scoring.drought_risk import calculate_drought_risk

        result = calculate_drought_risk(
            rainfall=200.0,
            historical_mean_rainfall=100.0,
            max_temp=28.0,
            historical_mean_temp=28.0,
        )
        assert result.rainfall_deficit_contribution == 0.0


class TestCompositeRiskScoring:
    """Test composite risk scoring."""

    def test_equal_weights(self):
        from risk.scoring.composite_risk import calculate_composite_risk

        result = calculate_composite_risk(heat_score=50.0, flood_score=50.0, drought_score=50.0)
        assert result.score == 50.0

    def test_one_dominant_risk(self):
        from risk.scoring.composite_risk import calculate_composite_risk

        result = calculate_composite_risk(heat_score=100.0, flood_score=0.0, drought_score=0.0)
        assert result.score == 33.0

    def test_score_bounded_0_100(self):
        from risk.scoring.composite_risk import calculate_composite_risk

        result = calculate_composite_risk(heat_score=100.0, flood_score=100.0, drought_score=100.0)
        assert result.score == 100.0

    def test_custom_weights(self):
        from risk.scoring.composite_risk import calculate_composite_risk

        weights = {"heat": 1.0, "flood": 0.0, "drought": 0.0}
        result = calculate_composite_risk(heat_score=80.0, flood_score=50.0, drought_score=50.0, weights=weights)
        assert result.score == 80.0
