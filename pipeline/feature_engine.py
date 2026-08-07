"""Feature engineering pipeline for climate time series data.

Generates temporal, lag, rolling window, seasonal, derived, spatial,
and interaction features from raw observation DataFrames.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

with contextlib.suppress(ImportError):
    from climatedt.storage.feature_store import FeatureStore  # noqa: F401
from pipeline.features import (
    add_prior_rainfall,
    add_rolling_features,
    add_temporal_features,
    round_feature_columns,
)

_logger = logging.getLogger(__name__)

_SEASON_MAP: dict[int, str] = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}

_INDIAN_MONSOON_MONTHS: list[int] = [6, 7, 8, 9]

_LATITUDE_BANDS: list[tuple[float, float, str]] = [
    (-90.0, -66.5, "polar_south"),
    (-66.5, -23.5, "temperate_south"),
    (-23.5, 0.0, "tropical_south"),
    (0.0, 23.5, "tropical_north"),
    (23.5, 66.5, "temperate_north"),
    (66.5, 90.0, "polar_north"),
]


@dataclass
class FeatureMetadata:
    """Metadata about a generated feature.

    Attributes:
        name: Feature name.
        feature_group: Feature group (temporal, lag, rolling, seasonal,
            derived, spatial, interaction).
        description: Human-readable description of the feature.
        data_type: Data type ('float', 'int', 'bool', 'category').
        source_columns: List of source columns used to create this feature.
        transform: Transform applied.
        nullable: Whether this feature can contain null values.
    """

    name: str
    feature_group: str
    description: str
    data_type: str = "float"
    source_columns: list[str] = field(default_factory=list)
    transform: str = "identity"
    nullable: bool = False


class FeatureEngine:
    """Feature engineering for climate time series data.

    Generates temporal, lag, rolling window, seasonal, derived,
    spatial, and interaction features from raw observation DataFrames.
    Delegates to pipeline.features for canonical feature generation
    and provides additional advanced features from the BHAI pipeline.
    """

    def __init__(self, feature_store: Any | None = None) -> None:
        """Initialize the feature engine.

        Args:
            feature_store: Optional FeatureStore for registering generated
                features. If provided, features are auto-registered.
        """
        self._feature_store = feature_store
        self._monsoon_months: list[int] = list(_INDIAN_MONSOON_MONTHS)
        self._feature_names: list[str] = []
        self._feature_metadata: dict[str, FeatureMetadata] = {}

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all feature engineering steps to a DataFrame.

        Runs the canonical pipeline.features steps first, then adds
        advanced BHAI features (lag, rolling, seasonal, derived,
        spatial, interaction).

        Args:
            df: Input DataFrame with weather observation columns.

        Returns:
            DataFrame with original columns plus all generated features.
        """
        result = df.copy()

        # Step 1: Run canonical feature engineering
        result = self._run_canonical_features(result)

        # Step 2: Detect available advanced columns
        has_timestamp = "timestamp" in result.columns or "Date" in result.columns
        ts_col = "timestamp" if "timestamp" in result.columns else "Date"
        has_temp = "temperature_2m" in result.columns or "MaxTemp" in result.columns
        temp_col = "temperature_2m" if "temperature_2m" in result.columns else "MaxTemp"
        has_precip = "precipitation_mm" in result.columns or "Rainfall" in result.columns
        precip_col = "precipitation_mm" if "precipitation_mm" in result.columns else "Rainfall"
        has_humidity = "humidity_pct" in result.columns
        has_lat = "latitude" in result.columns or "Latitude" in result.columns
        lat_col = "latitude" if "latitude" in result.columns else "Latitude"
        has_lon = "longitude" in result.columns or "Longitude" in result.columns
        lon_col = "longitude" if "longitude" in result.columns else "Longitude"
        # Temporal features (advanced)
        if has_timestamp:
            result = self.create_seasonal_features(result, ts_col)

        # Lag features
        lag_cols = []
        if has_temp:
            lag_cols.append(temp_col)
        if has_precip:
            lag_cols.append(precip_col)
        if has_humidity:
            lag_cols.append("humidity_pct")
        if lag_cols:
            result = self.create_lag_features(result, lag_cols, [1, 3, 6, 12, 24])

        # Rolling features (advanced)
        rolling_cols = []
        if has_temp:
            rolling_cols.append(temp_col)
        if has_precip:
            rolling_cols.append(precip_col)
        if has_humidity:
            rolling_cols.append("humidity_pct")
        if rolling_cols:
            result = self.create_rolling_features(result, rolling_cols, [3, 7, 14, 30])

        # Spatial features
        if has_lat:
            result = self._add_latitude_band(result, lat_col)
        if has_lon:
            result = self._add_longitude_zone(result, lon_col)

        # Interaction features
        interactions = []
        if has_temp and has_humidity:
            interactions.append((temp_col, "humidity_pct"))
        if has_temp and has_precip:
            interactions.append((temp_col, precip_col))
        if interactions:
            result = self.create_interaction_features(result, interactions)

        # Derived features
        if has_temp:
            result = self._add_diurnal_features(result, temp_col)
        if has_precip:
            result = self._add_precip_intensity(result, precip_col)
        if has_humidity:
            result = self._add_humidity_index(result)

        # Update feature tracking
        self._feature_names = [c for c in result.columns if c not in df.columns]

        return result

    def _run_canonical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the canonical pipeline feature engineering steps."""
        result = df.copy()

        # Map column names for canonical pipeline
        col_mapping = {}
        if "Date" not in result.columns and "timestamp" in result.columns:
            col_mapping["Date"] = result["timestamp"]
        if "MaxTemp" not in result.columns and "temperature_2m" in result.columns:
            col_mapping["MaxTemp"] = result["temperature_2m"]
        if "MinTemp" not in result.columns and "temperature_2m_min" in result.columns:
            col_mapping["MinTemp"] = result["temperature_2m_min"]
        if "Rainfall" not in result.columns and "precipitation_mm" in result.columns:
            col_mapping["Rainfall"] = result["precipitation_mm"]
        if "Latitude" not in result.columns and "latitude" in result.columns:
            col_mapping["Latitude"] = result["latitude"]
        if "Longitude" not in result.columns and "longitude" in result.columns:
            col_mapping["Longitude"] = result["longitude"]

        for col_name, col_data in col_mapping.items():
            result[col_name] = col_data

        has_canonical = all(
            c in result.columns for c in ["Date", "MaxTemp", "Rainfall", "Latitude", "Longitude"]
        )
        if has_canonical:
            result = add_temporal_features(result)
            result = add_rolling_features(result)
            result = add_prior_rainfall(result)
            result = round_feature_columns(result)

        return result

    def create_lag_features(
        self,
        df: pd.DataFrame,
        columns: list[str],
        lags: list[int],
    ) -> pd.DataFrame:
        """Create lagged versions of specified columns.

        Args:
            df: Input DataFrame sorted by timestamp.
            columns: Column names to create lags for.
            lags: Lag values in hours.

        Returns:
            DataFrame with added lag columns.
        """
        result = df.copy()

        for col in columns:
            for lag_hours in lags:
                lag_name = f"{col}_lag_{lag_hours}h"
                result[lag_name] = result[col].shift(lag_hours)
                self._register_feature_meta(
                    FeatureMetadata(
                        name=lag_name,
                        feature_group="lag",
                        description=f"Lag {lag_hours}h of {col}",
                        data_type="float",
                        source_columns=[col],
                        transform=f"lag_{lag_hours}h",
                        nullable=True,
                    )
                )

        return result

    def create_rolling_features(
        self,
        df: pd.DataFrame,
        columns: list[str],
        windows: list[int],
    ) -> pd.DataFrame:
        """Create rolling window statistics for specified columns.

        Generates rolling mean and standard deviation for each window.

        Args:
            df: Input DataFrame.
            columns: Column names to compute rolling stats for.
            windows: Window sizes in hours.

        Returns:
            DataFrame with added rolling feature columns.
        """
        result = df.copy()

        for col in columns:
            for window_hours in windows:
                mean_name = f"{col}_rolling_mean_{window_hours}h"
                result[mean_name] = result[col].rolling(window=window_hours, min_periods=1).mean()
                self._register_feature_meta(
                    FeatureMetadata(
                        name=mean_name,
                        feature_group="rolling",
                        description=f"Rolling mean of {col} over {window_hours}h",
                        data_type="float",
                        source_columns=[col],
                        transform=f"rolling_mean_{window_hours}h",
                        nullable=True,
                    )
                )

                std_name = f"{col}_rolling_std_{window_hours}h"
                result[std_name] = result[col].rolling(window=window_hours, min_periods=1).std()
                self._register_feature_meta(
                    FeatureMetadata(
                        name=std_name,
                        feature_group="rolling",
                        description=f"Rolling std of {col} over {window_hours}h",
                        data_type="float",
                        source_columns=[col],
                        transform=f"rolling_std_{window_hours}h",
                        nullable=True,
                    )
                )

        return result

    def create_seasonal_features(
        self,
        df: pd.DataFrame,
        date_column: str,
    ) -> pd.DataFrame:
        """Create seasonal and calendar features from a date column.

        Generates: hour, day, month, season, day_of_year, is_weekend,
        is_monsoon, quarter, day_of_week.

        Args:
            df: Input DataFrame.
            date_column: Name of the datetime column.

        Returns:
            DataFrame with added seasonal feature columns.
        """
        result = df.copy()
        dates = pd.to_datetime(result[date_column])

        result["hour"] = dates.dt.hour.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="hour",
                feature_group="temporal",
                description="Hour of day (0-23)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_hour",
            )
        )

        result["day"] = dates.dt.day.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="day",
                feature_group="temporal",
                description="Day of month (1-31)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_day",
            )
        )

        result["month"] = dates.dt.month.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="month",
                feature_group="temporal",
                description="Month (1-12)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_month",
            )
        )

        result["season"] = dates.dt.month.map(_SEASON_MAP)
        self._register_feature_meta(
            FeatureMetadata(
                name="season",
                feature_group="seasonal",
                description="Meteorological season (spring, summer, autumn, winter)",
                data_type="category",
                source_columns=[date_column],
                transform="month_to_season",
            )
        )

        result["day_of_year"] = dates.dt.dayofyear.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="day_of_year",
                feature_group="temporal",
                description="Day of year (1-366)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_dayofyear",
            )
        )

        result["is_weekend"] = (dates.dt.dayofweek >= 5).astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="is_weekend",
                feature_group="temporal",
                description="Is weekend (Saturday or Sunday)",
                data_type="int",
                source_columns=[date_column],
                transform="is_weekend",
            )
        )

        result["is_monsoon"] = dates.dt.month.isin(self._monsoon_months).astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="is_monsoon",
                feature_group="seasonal",
                description="Is Indian monsoon season (Jun-Sep)",
                data_type="int",
                source_columns=[date_column],
                transform="is_monsoon",
            )
        )

        result["quarter"] = dates.dt.quarter.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="quarter",
                feature_group="temporal",
                description="Calendar quarter (1-4)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_quarter",
            )
        )

        result["day_of_week"] = dates.dt.dayofweek.astype(np.int32)
        self._register_feature_meta(
            FeatureMetadata(
                name="day_of_week",
                feature_group="temporal",
                description="Day of week (0=Monday, 6=Sunday)",
                data_type="int",
                source_columns=[date_column],
                transform="extract_dayofweek",
            )
        )

        return result

    def create_spatial_features(
        self,
        df: pd.DataFrame,
        location_registry: Any,
    ) -> pd.DataFrame:
        """Create spatial features from location registry.

        Args:
            df: Input DataFrame with a 'location_id' column.
            location_registry: LocationRegistry instance.

        Returns:
            DataFrame with added spatial feature columns.
        """
        result = df.copy()

        if "location_id" not in result.columns:
            _logger.warning("No location_id column found for spatial features")
            return result

        loc_data = {}
        for loc_id in result["location_id"].unique():
            loc = location_registry.get_location(loc_id)
            if loc is not None:
                loc_data[loc_id] = loc

        if not loc_data:
            _logger.warning("No location data found for spatial features")
            return result

        result["elevation_m"] = result["location_id"].map(
            {lid: loc.elevation_m for lid, loc in loc_data.items()}
        )
        self._register_feature_meta(
            FeatureMetadata(
                name="elevation_m",
                feature_group="spatial",
                description="Elevation in meters above sea level",
                data_type="float",
                source_columns=["location_id"],
                transform="lookup_elevation",
                nullable=True,
            )
        )

        result["latitude_band"] = result["location_id"].map(
            {lid: self._classify_latitude_band(loc.latitude) for lid, loc in loc_data.items()}
        )
        self._register_feature_meta(
            FeatureMetadata(
                name="latitude_band",
                feature_group="spatial",
                description="Latitude band classification",
                data_type="category",
                source_columns=["location_id"],
                transform="classify_latitude",
            )
        )

        result["climate_zone"] = result.apply(
            lambda row: self._classify_climate_zone(
                row.get("latitude_band", "unknown"),
                row.get("elevation_m", 0.0),
            ),
            axis=1,
        )
        self._register_feature_meta(
            FeatureMetadata(
                name="climate_zone",
                feature_group="spatial",
                description="Climate zone classification",
                data_type="category",
                source_columns=["latitude_band", "elevation_m"],
                transform="classify_climate_zone",
            )
        )

        return result

    def create_interaction_features(
        self,
        df: pd.DataFrame,
        interactions: list[tuple[str, str]],
    ) -> pd.DataFrame:
        """Create interaction features between pairs of columns.

        For each pair (col_a, col_b), generates:
        - col_a * col_b (multiplication)
        - col_a / (col_b + epsilon) (ratio)

        Args:
            df: Input DataFrame.
            interactions: List of (column_a, column_b) pairs.

        Returns:
            DataFrame with added interaction feature columns.
        """
        result = df.copy()
        epsilon = 1e-10

        for col_a, col_b in interactions:
            if col_a not in result.columns or col_b not in result.columns:
                continue

            mult_name = f"{col_a}_{col_b}_interaction"
            result[mult_name] = result[col_a] * result[col_b]
            self._register_feature_meta(
                FeatureMetadata(
                    name=mult_name,
                    feature_group="interaction",
                    description=f"Interaction ({col_a} * {col_b})",
                    data_type="float",
                    source_columns=[col_a, col_b],
                    transform="multiplication",
                )
            )

            ratio_name = f"{col_a}_{col_b}_ratio"
            result[ratio_name] = result[col_a] / (result[col_b].abs() + epsilon)
            self._register_feature_meta(
                FeatureMetadata(
                    name=ratio_name,
                    feature_group="interaction",
                    description=f"Ratio ({col_a} / {col_b})",
                    data_type="float",
                    source_columns=[col_a, col_b],
                    transform="ratio",
                )
            )

        return result

    def get_feature_names(self) -> list[str]:
        return list(self._feature_names)

    def get_feature_metadata(self) -> dict[str, FeatureMetadata]:
        return dict(self._feature_metadata)

    def set_monsoon_months(self, months: list[int]) -> None:
        self._monsoon_months = list(months)

    def _register_feature_meta(self, meta: FeatureMetadata) -> None:
        self._feature_metadata[meta.name] = meta
        if self._feature_store is not None:
            try:
                self._feature_store.register_feature(
                    name=meta.name,
                    definition=meta.transform,
                    version="1.0",
                    feature_type=meta.data_type,
                    domain="forecasting",
                    source="ml_pipeline",
                    description=meta.description,
                    metadata={
                        "feature_group": meta.feature_group,
                        "source_columns": ",".join(meta.source_columns),
                        "nullable": str(meta.nullable),
                    },
                )
            except Exception as exc:
                _logger.warning("Failed to register feature in store: %s", exc)

    def _add_latitude_band(self, df: pd.DataFrame, lat_col: str = "latitude") -> pd.DataFrame:
        if lat_col not in df.columns:
            return df
        result = df.copy()
        result["latitude_band"] = result[lat_col].apply(self._classify_latitude_band)
        self._register_feature_meta(
            FeatureMetadata(
                name="latitude_band",
                feature_group="spatial",
                description="Latitude band classification",
                data_type="category",
                source_columns=[lat_col],
                transform="classify_latitude",
            )
        )
        return result

    def _add_longitude_zone(self, df: pd.DataFrame, lon_col: str = "longitude") -> pd.DataFrame:
        if lon_col not in df.columns:
            return df
        result = df.copy()

        def _classify_lon_zone(lon: float) -> str:
            if lon < -90:
                return "west"
            elif lon < 0:
                return "central_west"
            elif lon < 90:
                return "central_east"
            else:
                return "east"

        result["longitude_zone"] = result[lon_col].apply(_classify_lon_zone)
        self._register_feature_meta(
            FeatureMetadata(
                name="longitude_zone",
                feature_group="spatial",
                description="Longitude zone classification",
                data_type="category",
                source_columns=[lon_col],
                transform="classify_longitude",
            )
        )
        return result

    def _add_diurnal_features(
        self, df: pd.DataFrame, temp_col: str = "temperature_2m"
    ) -> pd.DataFrame:
        result = df.copy()
        if temp_col not in result.columns:
            return result

        result["diurnal_range"] = (
            result[temp_col].rolling(window=24, min_periods=1).max()
            - result[temp_col].rolling(window=24, min_periods=1).min()
        )
        self._register_feature_meta(
            FeatureMetadata(
                name="diurnal_range",
                feature_group="derived",
                description="Diurnal temperature range (24h max-min)",
                data_type="float",
                source_columns=[temp_col],
                transform="rolling_24h_range",
                nullable=True,
            )
        )

        return result

    def _add_precip_intensity(
        self, df: pd.DataFrame, precip_col: str = "precipitation_mm"
    ) -> pd.DataFrame:
        result = df.copy()
        if precip_col not in result.columns:
            return result

        def _precip_category(val: float) -> str:
            if val <= 0.0:
                return "none"
            elif val < 2.5:
                return "light"
            elif val < 10.0:
                return "moderate"
            elif val < 50.0:
                return "heavy"
            else:
                return "extreme"

        result["precipitation_intensity"] = result[precip_col].apply(_precip_category)
        self._register_feature_meta(
            FeatureMetadata(
                name="precipitation_intensity",
                feature_group="derived",
                description="Precipitation intensity category",
                data_type="category",
                source_columns=[precip_col],
                transform="classify_precip_intensity",
            )
        )

        return result

    def _add_humidity_index(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        if "humidity_pct" not in result.columns:
            return result

        def _humidity_category(val: float) -> str:
            if val < 30:
                return "dry"
            elif val < 50:
                return "comfortable"
            elif val < 70:
                return "humid"
            else:
                return "very_humid"

        result["humidity_index"] = result["humidity_pct"].apply(_humidity_category)
        self._register_feature_meta(
            FeatureMetadata(
                name="humidity_index",
                feature_group="derived",
                description="Humidity comfort index category",
                data_type="category",
                source_columns=["humidity_pct"],
                transform="classify_humidity",
            )
        )

        return result

    @staticmethod
    def _classify_latitude_band(lat: float) -> str:
        for lower, upper, band in _LATITUDE_BANDS:
            if lower <= lat < upper:
                return band
        return "unknown"

    @staticmethod
    def _classify_climate_zone(latitude_band: str, elevation_m: float) -> str:
        if elevation_m > 2500:
            return "alpine"
        if elevation_m > 1500:
            return "highland"
        if latitude_band in ("tropical_north", "tropical_south"):
            if elevation_m > 500:
                return "tropical_highland"
            return "tropical"
        if latitude_band in ("temperate_north", "temperate_south"):
            return "temperate"
        if latitude_band in ("polar_north", "polar_south"):
            return "polar"
        return "unknown"


__all__ = [
    "FeatureEngine",
    "FeatureMetadata",
]
