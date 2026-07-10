from datetime import UTC, datetime

import pytest

from simulator.models.forecast import ForecastPoint, ForecastSeries, ForecastValidation


def make_point(temp=25.0, humid=50.0, wdir=180.0, lat=10.0, lon=20.0):
    return ForecastPoint(
        location_id="loc1",
        latitude=lat,
        longitude=lon,
        forecast_timestamp=datetime(2024, 6, 15, 12, tzinfo=UTC),
        issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
        temperature_2m=temp,
        precipitation_mm=0.0,
        humidity_pct=humid,
        pressure_hpa=1013.0,
        wind_speed_10m=5.0,
        wind_direction_10m=wdir,
    )


class TestForecastPoint:
    def test_create(self):
        fp = make_point()
        assert fp.location_id == "loc1"
        assert fp.temperature_2m == 25.0
        assert len(fp.point_id) == 16

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            make_point(lat=100.0)
        with pytest.raises(ValueError, match="Latitude"):
            make_point(lat=-100.0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            make_point(lon=200.0)
        with pytest.raises(ValueError, match="Longitude"):
            make_point(lon=-200.0)

    def test_invalid_humidity(self):
        with pytest.raises(ValueError, match="Humidity"):
            make_point(humid=150.0)
        with pytest.raises(ValueError, match="Humidity"):
            make_point(humid=-10.0)

    def test_invalid_wind_direction(self):
        with pytest.raises(ValueError, match="Wind direction"):
            make_point(wdir=400.0)
        with pytest.raises(ValueError, match="Wind direction"):
            make_point(wdir=-10.0)

    def test_valid_boundaries(self):
        fp = make_point(lat=90.0, lon=180.0, humid=0.0, wdir=0.0)
        assert fp.latitude == 90.0
        fp2 = make_point(lat=-90.0, lon=-180.0, humid=100.0, wdir=359.9)
        assert fp2.humidity_pct == 100.0

    def test_optional_fields(self):
        fp = make_point()
        assert fp.cloud_cover_pct is None
        assert fp.solar_radiation is None
        assert fp.ensemble_member == 0
        assert fp.model_name == "unknown"

    def test_confidence_intervals(self):
        fp = make_point()
        fp.confidence_interval_lower = 23.0
        fp.confidence_interval_upper = 27.0
        assert fp.confidence_interval_lower == 23.0


class TestForecastSeries:
    def test_create(self):
        points = [make_point(), make_point(temp=30.0)]
        series = ForecastSeries(
            location_id="loc1",
            latitude=10.0,
            longitude=20.0,
            points=points,
            model_name="gfs",
            issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
            horizon_hours=48,
        )
        assert len(series.points) == 2
        assert series.horizon_hours == 48
        assert len(series.series_id) == 16

    def test_empty_points_raises(self):
        with pytest.raises(ValueError, match="at least one point"):
            ForecastSeries(
                location_id="loc1",
                latitude=10.0,
                longitude=20.0,
                points=[],
                model_name="gfs",
                issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                horizon_hours=48,
            )

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            ForecastSeries(
                location_id="loc1",
                latitude=100.0,
                longitude=20.0,
                points=[make_point()],
                model_name="gfs",
                issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                horizon_hours=48,
            )

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            ForecastSeries(
                location_id="loc1",
                latitude=10.0,
                longitude=200.0,
                points=[make_point()],
                model_name="gfs",
                issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                horizon_hours=48,
            )

    def test_non_positive_horizon(self):
        with pytest.raises(ValueError, match="Horizon hours must be positive"):
            ForecastSeries(
                location_id="loc1",
                latitude=10.0,
                longitude=20.0,
                points=[make_point()],
                model_name="gfs",
                issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                horizon_hours=0,
            )

    def test_variable_names(self):
        series = ForecastSeries(
            location_id="loc1",
            latitude=10.0,
            longitude=20.0,
            points=[make_point()],
            model_name="gfs",
            issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
            horizon_hours=48,
        )
        names = series.variable_names
        assert "temperature_2m" in names
        assert "precipitation_mm" in names
        assert "humidity_pct" in names
        assert len(names) == 6

    def test_metadata(self):
        series = ForecastSeries(
            location_id="loc1",
            latitude=10.0,
            longitude=20.0,
            points=[make_point()],
            model_name="gfs",
            issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
            horizon_hours=48,
            metadata={"key": "value"},
        )
        assert series.metadata["key"] == "value"


class TestForecastValidation:
    def test_create(self):
        fv = ForecastValidation(
            location_id="loc1",
            forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
            forecast_horizon_hours=48,
            model_name="gfs",
            variable="temperature_2m",
            mae=1.5,
            rmse=2.0,
        )
        assert fv.mae == 1.5
        assert fv.rmse == 2.0
        assert len(fv.validation_id) == 16

    def test_negative_mae_raises(self):
        with pytest.raises(ValueError, match="MAE"):
            ForecastValidation(
                location_id="loc1",
                forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                forecast_horizon_hours=48,
                model_name="gfs",
                variable="temperature_2m",
                mae=-1.0,
                rmse=2.0,
            )

    def test_negative_rmse_raises(self):
        with pytest.raises(ValueError, match="RMSE"):
            ForecastValidation(
                location_id="loc1",
                forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                forecast_horizon_hours=48,
                model_name="gfs",
                variable="temperature_2m",
                mae=1.0,
                rmse=-1.0,
            )

    def test_negative_mape_raises(self):
        with pytest.raises(ValueError, match="MAPE"):
            ForecastValidation(
                location_id="loc1",
                forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                forecast_horizon_hours=48,
                model_name="gfs",
                variable="temperature_2m",
                mae=1.0,
                rmse=2.0,
                mape=-1.0,
            )

    def test_negative_samples_raises(self):
        with pytest.raises(ValueError, match="Number of samples"):
            ForecastValidation(
                location_id="loc1",
                forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
                forecast_horizon_hours=48,
                model_name="gfs",
                variable="temperature_2m",
                mae=1.0,
                rmse=2.0,
                num_samples=-1,
            )

    def test_optional_fields(self):
        fv = ForecastValidation(
            location_id="loc1",
            forecast_issue_timestamp=datetime(2024, 6, 14, 12, tzinfo=UTC),
            forecast_horizon_hours=48,
            model_name="gfs",
            variable="temperature_2m",
            mae=1.5,
            rmse=2.0,
            bias=0.5,
            correlation=0.9,
            num_samples=100,
        )
        assert fv.bias == 0.5
        assert fv.correlation == 0.9
        assert fv.num_samples == 100
