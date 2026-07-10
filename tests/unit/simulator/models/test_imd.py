from datetime import date, datetime

import pytest

from simulator.models.imd import (
    IMD_DAILY_RAINFALL,
    IMD_DAILY_TEMPERATURE,
    IMD_FALLBACK_BASE_URL,
    IMD_GRIDDED_PRODUCTS,
    IMDDataProduct,
    IMDGridDefinition,
)


class TestIMDGridDefinition:
    def test_create(self):
        grid = IMDGridDefinition(
            product_name="Test Product",
            resolution_deg=0.25,
            lat_range=(6.5, 38.5),
            lon_range=(66.5, 100.5),
            time_range=(date(1901, 1, 1), date(2024, 12, 31)),
            variables=["precipitation_mm"],
        )
        assert grid.product_name == "Test Product"
        assert grid.resolution_deg == 0.25

    def test_negative_resolution_raises(self):
        with pytest.raises(ValueError, match="Grid resolution must be positive"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=-0.25,
                lat_range=(0, 10),
                lon_range=(0, 10),
                time_range=(date(2000, 1, 1), date(2020, 1, 1)),
                variables=["temp"],
            )

    def test_zero_resolution_raises(self):
        with pytest.raises(ValueError, match="Grid resolution must be positive"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0,
                lat_range=(0, 10),
                lon_range=(0, 10),
                time_range=(date(2000, 1, 1), date(2020, 1, 1)),
                variables=["temp"],
            )

    def test_invalid_lat_range(self):
        with pytest.raises(ValueError, match="Latitude range must be within"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(-100, 38.5),
                lon_range=(66.5, 100.5),
                time_range=(date(1901, 1, 1), date(2024, 12, 31)),
                variables=["precip"],
            )

    def test_invalid_lon_range(self):
        with pytest.raises(ValueError, match="Longitude range must be within"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(6.5, 38.5),
                lon_range=(-200, 100.5),
                time_range=(date(1901, 1, 1), date(2024, 12, 31)),
                variables=["precip"],
            )

    def test_lat_start_gte_end(self):
        with pytest.raises(ValueError, match="Latitude range start must be less than end"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(38.5, 6.5),
                lon_range=(66.5, 100.5),
                time_range=(date(1901, 1, 1), date(2024, 12, 31)),
                variables=["precip"],
            )

    def test_lon_start_gte_end(self):
        with pytest.raises(ValueError, match="Longitude range start must be less than end"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(6.5, 38.5),
                lon_range=(100.5, 66.5),
                time_range=(date(1901, 1, 1), date(2024, 12, 31)),
                variables=["precip"],
            )

    def test_time_range_start_gte_end(self):
        with pytest.raises(ValueError, match="Time range start"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(6.5, 38.5),
                lon_range=(66.5, 100.5),
                time_range=(date(2024, 12, 31), date(1901, 1, 1)),
                variables=["precip"],
            )

    def test_empty_product_name(self):
        with pytest.raises(ValueError, match="Product name must not be empty"):
            IMDGridDefinition(
                product_name="",
                resolution_deg=0.25,
                lat_range=(0, 10),
                lon_range=(0, 10),
                time_range=(date(2000, 1, 1), date(2020, 1, 1)),
                variables=["temp"],
            )

    def test_empty_variables(self):
        with pytest.raises(ValueError, match="Variables list must not be empty"):
            IMDGridDefinition(
                product_name="Test",
                resolution_deg=0.25,
                lat_range=(0, 10),
                lon_range=(0, 10),
                time_range=(date(2000, 1, 1), date(2020, 1, 1)),
                variables=[],
            )

    def test_lat_count(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        assert grid.lat_count == 6

    def test_lon_count(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        assert grid.lon_count == 11

    def test_total_grid_points(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        assert grid.total_grid_points == 66


class TestIMDDataProduct:
    def test_create(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        product = IMDDataProduct(
            grid=grid,
            file_url="https://example.com/data.nc",
            checksum="a" * 64,
            last_updated=datetime(2024, 1, 1),
        )
        assert product.grid is grid
        assert product.version == "1.0"

    def test_empty_url_raises(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(ValueError, match="File URL must not be empty"):
            IMDDataProduct(
                grid=grid,
                file_url="",
                checksum="a" * 64,
                last_updated=datetime(2024, 1, 1),
            )

    def test_empty_checksum_raises(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(ValueError, match="Checksum must not be empty"):
            IMDDataProduct(
                grid=grid,
                file_url="https://example.com",
                checksum="",
                last_updated=datetime(2024, 1, 1),
            )

    def test_empty_version_raises(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(ValueError, match="Version must not be empty"):
            IMDDataProduct(
                grid=grid,
                file_url="https://example.com",
                checksum="a" * 64,
                last_updated=datetime(2024, 1, 1),
                version="",
            )

    def test_invalid_checksum_length(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(ValueError, match="64-character"):
            IMDDataProduct(
                grid=grid,
                file_url="https://example.com",
                checksum="short",
                last_updated=datetime(2024, 1, 1),
            )

    def test_invalid_checksum_hex(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(ValueError, match="valid hex string"):
            IMDDataProduct(
                grid=grid,
                file_url="https://example.com",
                checksum="z" + "0" * 63,
                last_updated=datetime(2024, 1, 1),
            )

    def test_checksum_not_string(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        with pytest.raises(TypeError, match="Checksum must be a string"):
            IMDDataProduct(
                grid=grid,
                file_url="https://example.com",
                checksum=12345,
                last_updated=datetime(2024, 1, 1),
            )

    def test_verify_integrity(self):
        grid = IMDGridDefinition(
            product_name="Test",
            resolution_deg=1.0,
            lat_range=(0, 5),
            lon_range=(0, 10),
            time_range=(date(2000, 1, 1), date(2020, 1, 1)),
            variables=["temp"],
        )
        import hashlib

        data = b"test data"
        checksum = hashlib.sha256(data).hexdigest()
        product = IMDDataProduct(
            grid=grid,
            file_url="https://example.com",
            checksum=checksum,
            last_updated=datetime(2024, 1, 1),
        )
        assert product.verify_integrity(data) is True
        assert product.verify_integrity(b"tampered") is False


class TestConstants:
    def test_imd_daily_rainfall(self):
        assert IMD_DAILY_RAINFALL.product_name == "IMD Daily Rainfall"
        assert IMD_DAILY_RAINFALL.resolution_deg == 0.25
        assert IMD_DAILY_RAINFALL.lat_range == (6.5, 38.5)
        assert IMD_DAILY_RAINFALL.lon_range == (66.5, 100.5)

    def test_imd_daily_temperature(self):
        assert IMD_DAILY_TEMPERATURE.product_name == "IMD Daily Temperature"
        assert IMD_DAILY_TEMPERATURE.resolution_deg == 1.0
        assert "temperature_max_c" in IMD_DAILY_TEMPERATURE.variables
        assert "temperature_min_c" in IMD_DAILY_TEMPERATURE.variables

    def test_imd_gridded_products(self):
        assert "imd_daily_rainfall" in IMD_GRIDDED_PRODUCTS
        assert "imd_daily_temperature" in IMD_GRIDDED_PRODUCTS
        assert IMD_GRIDDED_PRODUCTS["imd_daily_rainfall"] is IMD_DAILY_RAINFALL
        assert IMD_GRIDDED_PRODUCTS["imd_daily_temperature"] is IMD_DAILY_TEMPERATURE

    def test_fallback_base_url(self):
        assert IMD_FALLBACK_BASE_URL == "https://archive-api.open-meteo.com/v1/archive"
