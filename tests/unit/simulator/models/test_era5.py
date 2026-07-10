import pytest

from simulator.models.era5 import (
    ERA5_CDS_BASE_URL,
    ERA5_CDS_DATASET,
    ERA5_VARIABLES,
    ERA5Request,
    ERA5Variable,
    ERA5VariableName,
)


class TestERA5VariableName:
    def test_values(self):
        assert ERA5VariableName.TEMPERATURE_2M.value == "2m_temperature"
        assert ERA5VariableName.TOTAL_PRECIPITATION.value == "total_precipitation"
        assert ERA5VariableName.SURFACE_PRESSURE.value == "surface_pressure"

    def test_has_expected_members(self):
        names = {m.name for m in ERA5VariableName}
        assert "TEMPERATURE_2M" in names
        assert "TOTAL_PRECIPITATION" in names
        assert "SURFACE_SOLAR_RADIATION" in names


class TestERA5Variable:
    def test_create(self):
        v = ERA5Variable(name="2m_temperature", description="Temperature at 2m", units="K")
        assert v.name == "2m_temperature"
        assert v.description == "Temperature at 2m"
        assert v.units == "K"
        assert v.pressure_level is False

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            ERA5Variable(name="", description="desc", units="K")

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description must not be empty"):
            ERA5Variable(name="var", description="", units="K")

    def test_empty_units_raises(self):
        with pytest.raises(ValueError, match="units must not be empty"):
            ERA5Variable(name="var", description="desc", units="")

    def test_api_name(self):
        v = ERA5Variable(name="2m_temperature", description="Temp", units="K")
        assert v.api_name == "2m_temperature"

    def test_pressure_level_flag(self):
        v = ERA5Variable(name="var", description="desc", units="hPa", pressure_level=True)
        assert v.pressure_level is True


class TestERA5Request:
    def test_create(self):
        req = ERA5Request(variable="2m_temperature", year=2020, month=6)
        assert req.variable == "2m_temperature"
        assert req.year == 2020
        assert req.month == 6
        assert req.product_type == "reanalysis"
        assert req.format == "netcdf"

    def test_empty_variable_raises(self):
        with pytest.raises(ValueError, match="Variable must not be empty"):
            ERA5Request(variable="", year=2020, month=1)

    def test_year_bounds(self):
        with pytest.raises(ValueError, match="Year must be between"):
            ERA5Request(variable="temp", year=1949, month=1)
        with pytest.raises(ValueError, match="Year must be between"):
            ERA5Request(variable="temp", year=2101, month=1)

    def test_month_bounds(self):
        with pytest.raises(ValueError, match="Month must be between"):
            ERA5Request(variable="temp", year=2020, month=0)
        with pytest.raises(ValueError, match="Month must be between"):
            ERA5Request(variable="temp", year=2020, month=13)

    def test_valid_year_month_edges(self):
        req = ERA5Request(variable="temp", year=1950, month=1)
        assert req.year == 1950
        req2 = ERA5Request(variable="temp", year=2100, month=12)
        assert req2.month == 12

    def test_invalid_product_type(self):
        with pytest.raises(ValueError, match="Product type"):
            ERA5Request(variable="temp", year=2020, month=1, product_type="invalid")

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Format must be"):
            ERA5Request(variable="temp", year=2020, month=1, format="csv")

    def test_area(self):
        req = ERA5Request(variable="temp", year=2020, month=1, area=[10, 70, 20, 80])
        assert req.area == [10, 70, 20, 80]

    def test_pressure_level(self):
        req = ERA5Request(variable="temp", year=2020, month=1, pressure_level="850")
        assert req.pressure_level == "850"

    def test_metadata(self):
        req = ERA5Request(variable="temp", year=2020, month=1, metadata={"key": "val"})
        assert req.metadata["key"] == "val"


class TestERA5Variables:
    def test_is_dict(self):
        assert isinstance(ERA5_VARIABLES, dict)

    def test_has_expected_keys(self):
        assert "2m_temperature" in ERA5_VARIABLES
        assert "total_precipitation" in ERA5_VARIABLES
        assert "surface_pressure" in ERA5_VARIABLES

    def test_values_are_era5_variable(self):
        for v in ERA5_VARIABLES.values():
            assert isinstance(v, ERA5Variable)

    def test_specific_variable(self):
        v = ERA5_VARIABLES["2m_temperature"]
        assert v.units == "K"
        assert v.description == "Temperature at 2 metres above the surface"


class TestConstants:
    def test_cds_base_url(self):
        assert ERA5_CDS_BASE_URL == "https://cds.climate.copernicus.eu/api"

    def test_cds_dataset(self):
        assert ERA5_CDS_DATASET == "reanalysis-era5-single-levels"
