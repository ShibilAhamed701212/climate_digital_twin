from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ERA5VariableName(StrEnum):
    TEMPERATURE_2M = "2m_temperature"
    DEWPOINT_2M = "2m_dewpoint_temperature"
    TOTAL_PRECIPITATION = "total_precipitation"
    SURFACE_PRESSURE = "surface_pressure"
    MEAN_SEA_LEVEL_PRESSURE = "mean_sea_level_pressure"
    U_WIND_10M = "10m_u_component_of_wind"
    V_WIND_10M = "10m_v_component_of_wind"
    SKIN_TEMPERATURE = "skin_temperature"
    SOIL_TEMPERATURE_1 = "soil_temperature_level_1"
    SOIL_MOISTURE_1 = "volumetric_soil_water_layer_1"
    SNOW_DEPTH = "snow_depth"
    CLOUD_COVER_TOTAL = "total_cloud_cover"
    SURFACE_SOLAR_RADIATION = "surface_solar_radiation_downwards"
    SURFACE_THERMAL_RADIATION = "surface_thermal_radiation_downwards"
    EVAPORATION = "evaporation"
    RUNOFF = "runoff"


@dataclass
class ERA5Variable:
    name: str
    description: str
    units: str
    pressure_level: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Variable name must not be empty")
        if not self.description:
            raise ValueError("Variable description must not be empty")
        if not self.units:
            raise ValueError("Variable units must not be empty")

    @property
    def api_name(self) -> str:
        return self.name


@dataclass
class ERA5Request:
    variable: str
    year: int
    month: int
    pressure_level: str | None = None
    product_type: str = "reanalysis"
    time_slot: str = "12:00"
    area: list[float] | None = None
    format: str = "netcdf"
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.variable:
            raise ValueError("Variable must not be empty")
        if not 1950 <= self.year <= 2100:
            raise ValueError(f"Year must be between 1950 and 2100, got {self.year}")
        if not 1 <= self.month <= 12:
            raise ValueError(f"Month must be between 1 and 12, got {self.month}")
        if self.product_type not in ("reanalysis", "ensemble_members"):
            raise ValueError(
                f"Product type must be 'reanalysis' or 'ensemble_members', got {self.product_type}"
            )
        if self.format not in ("netcdf", "grib"):
            raise ValueError(f"Format must be 'netcdf' or 'grib', got {self.format}")


ERA5_VARIABLES: dict[str, ERA5Variable] = {
    "2m_temperature": ERA5Variable(
        name="2m_temperature",
        description="Temperature at 2 metres above the surface",
        units="K",
    ),
    "2m_dewpoint_temperature": ERA5Variable(
        name="2m_dewpoint_temperature",
        description="Dewpoint temperature at 2 metres above the surface",
        units="K",
    ),
    "total_precipitation": ERA5Variable(
        name="total_precipitation",
        description="Accumulated precipitation (rain + snow)",
        units="m",
    ),
    "surface_pressure": ERA5Variable(
        name="surface_pressure",
        description="Surface atmospheric pressure",
        units="Pa",
    ),
    "mean_sea_level_pressure": ERA5Variable(
        name="mean_sea_level_pressure",
        description="Mean sea level pressure",
        units="Pa",
    ),
    "10m_u_component_of_wind": ERA5Variable(
        name="10m_u_component_of_wind",
        description="U-component (eastward) wind at 10 metres",
        units="m/s",
    ),
    "10m_v_component_of_wind": ERA5Variable(
        name="10m_v_component_of_wind",
        description="V-component (northward) wind at 10 metres",
        units="m/s",
    ),
    "total_cloud_cover": ERA5Variable(
        name="total_cloud_cover",
        description="Total cloud cover fraction",
        units="(0–1)",
    ),
    "surface_solar_radiation_downwards": ERA5Variable(
        name="surface_solar_radiation_downwards",
        description="Surface solar radiation downwards",
        units="J/m²",
    ),
    "volumetric_soil_water_layer_1": ERA5Variable(
        name="volumetric_soil_water_layer_1",
        description="Volumetric soil water in layer 1 (0–7 cm)",
        units="m³/m³",
    ),
}

ERA5_CDS_BASE_URL = "https://cds.climate.copernicus.eu/api"
ERA5_CDS_DATASET = "reanalysis-era5-single-levels"

__all__ = [
    "ERA5VariableName",
    "ERA5Variable",
    "ERA5Request",
    "ERA5_VARIABLES",
    "ERA5_CDS_BASE_URL",
    "ERA5_CDS_DATASET",
]
