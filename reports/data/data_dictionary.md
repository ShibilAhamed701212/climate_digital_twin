# Data Dictionary — Climate Digital Twin

## Overview

The dataset contains **11 feature columns** and **3 target columns** across 14 total columns in the processed splits. Features are engineered from raw NASA POWER climate data through cleaning and feature engineering pipelines in `pipeline/clean.py` and `pipeline/features.py`.

---

## Column Dictionary

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `Date` | `string` | Calendar date in YYYY-MM-DD format. Used as temporal index for sequence windowing. | Raw data (normalized in `clean.py`) |
| `Latitude` | `float64` | Latitude of grid cell centre in decimal degrees (°N). Karnataka coverage: 11.5–18.5. | Raw data (validated in `clean.py`) |
| `Longitude` | `float64` | Longitude of grid cell centre in decimal degrees (°E). Karnataka coverage: 74.0–78.0. | Raw data (validated in `clean.py`) |
| `Month` | `int64` | Calendar month extracted from Date (1–12). Used for seasonal decomposition. | `features.add_temporal_features()` |
| `Week` | `int64` | ISO week number extracted from Date (1–53). Captures sub-month seasonality. | `features.add_temporal_features()` |
| `Season` | `string` | Season label mapped from Month: Winter (1,2,12), Summer (3–5), Monsoon (6–9), Post-Monsoon (10,11). | `features.add_temporal_features()` |
| `Monsoon` | `int64` | Binary monsoon indicator: 1 if Month in [6,7,8,9], else 0. | `features.add_temporal_features()` |
| `RollingRain7` | `float64` | 7-day rolling mean of rainfall preceding the current date. Captures short-term precipitation trends. | `features.add_rolling_features()` |
| `RollingRain30` | `float64` | 30-day rolling mean of rainfall preceding the current date. Captures medium-term precipitation trends. | `features.add_rolling_features()` |
| `RollingTemp7` | `float64` | 7-day rolling mean of MaxTemp preceding the current date. Captures short-term temperature trends. | `features.add_rolling_features()` |
| `RollingTemp30` | `float64` | 30-day rolling mean of MaxTemp preceding the current date. Captures medium-term temperature trends. | `features.add_rolling_features()` |
| `Rainfall` | `float64` | **Target:** Daily rainfall total in millimetres (mm). Also used as a feature for rolling computations. Clipped to [0, 500] mm/day. | Raw `rainfall.parquet` (cleaned in `clean.py`) |
| `MaxTemp` | `float64` | **Target:** Daily maximum temperature in degrees Celsius (°C). Also used as a feature for rolling computations. Clipped to [–10, 55] °C. | Raw `maxtemp.parquet` (cleaned in `clean.py`) |
| `MinTemp` | `float64` | **Target:** Daily minimum temperature in degrees Celsius (°C). Clipped to [–10, 55] °C. | Raw `mintemp.parquet` (cleaned in `clean.py`) |

### Additional Engineered Features (in `featured_data.parquet` only)

These features exist in the interim `featured_data.parquet` but are **not** included in the final processed CSV splits used for model training:

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `DayOfYear` | `int64` | Day of year (1–366). Used in feature engineering but not selected for model input. | `features.add_temporal_features()` |
| `RainfallTrend` | `float64` | Linear trend slope of rainfall over 30-day window. Polyfit slope over rolling window. | `features.add_rolling_features()` |
| `TempDiff` | `float64` | Diurnal temperature range: `MaxTemp - MinTemp`. | `features.add_rolling_features()` |
| `PriorRain7` | `float64` | Sum of rainfall over previous 7 days (shifted, not including current day). | `features.add_prior_rainfall()` |
| `PriorRain30` | `float64` | Sum of rainfall over previous 30 days (shifted, not including current day). | `features.add_prior_rainfall()` |

---

## Data Cleaning Steps (`pipeline/clean.py`)

1. **Remove duplicates** — drop_duplicates with keep="first"
2. **Normalize dates** — convert to datetime, coerce errors, drop invalid
3. **Standardize units** — rainfall in mm, temperature in °C; clamp negative rainfall to 0
4. **Correct coordinates** — remove records outside configured lat/lon bounds
5. **Clip outliers** — Rainfall clipped to [1st, 99th] percentiles; MaxTemp/MinTemp clipped to [0.1th, 99.9th] percentiles
6. **Handle missing values** — linear interpolation with backward/forward fill, then median fill for remaining
7. **Merge datasets** — outer join on (Date, Latitude, Longitude)
8. **StandardScaler** — applied per-feature during data loading (`data_loader.py`)

---

## Feature Engineering Steps (`pipeline/features.py`)

1. **Temporal features:** DayOfYear, Month, Week, Season (mapped), Monsoon (binary)
2. **Rolling features:** RollingRain7, RollingRain30, RollingTemp7, RollingTemp30 (grouped by lat/lon)
3. **Rainfall trend:** Linear slope over 30-day window
4. **TempDiff:** MaxTemp − MinTemp
5. **Prior rainfall:** Shifted 7-day and 30-day rainfall sums
6. **Rounding:** All float columns rounded to 2 decimal places (except Month, Week, DayOfYear, Monsoon, Lat, Lon)

---

## Feature Count: 11 + 3

**11 Features:** Rainfall, MaxTemp, MinTemp, Month, Week, Season, Monsoon, RollingRain7, RollingRain30, RollingTemp7, RollingTemp30

**3 Targets:** Rainfall, MaxTemp, MinTemp
