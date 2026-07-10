# Dataset Report — Climate Digital Twin

## Overview

The dataset covers daily climate measurements across **Karnataka, India** from **1981-01-01 to 2023-12-31**, gridded at 0.5° resolution. It comprises **753,840 raw observations** at **48 unique grid locations** (8 latitudes × 6 longitudes) over 15,705 days.

---

## Data Flow

```
Raw Parquet (3 files) → Clean/Interim → Feature Engineering → Processed CSV splits
```

---

## Raw Data (`data/raw/`)

| File | Rows | Columns | Variable | Date Range |
|------|------|---------|----------|------------|
| `rainfall.parquet` | 753,840 | 4 | Rainfall (mm) | 1981-01-01 – 2023-12-31 |
| `maxtemp.parquet` | 753,840 | 4 | MaxTemp (°C) | 1981-01-01 – 2023-12-31 |
| `mintemp.parquet` | 753,840 | 4 | MinTemp (°C) | 1981-01-01 – 2023-12-31 |

Each raw file has columns: `Date`, `Latitude`, `Longitude`, and the measurement variable.

### Spatial Coverage (Raw)

- **Latitude:** 11.5°N to 18.5°N (8 unique values: 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5)
- **Longitude:** 74.0°E to 79.0°E (6 unique values: 74, 75, 76, 77, 78, 79)
- **Grid resolution:** 0.5° × 0.5°
- **Total grid cells:** 48

---

## Interim Data (`data/interim/`)

| File | Rows | Columns | Description |
|------|------|---------|-------------|
| `cleaned_data.parquet` | 628,200 | 6 | After dedup, missing value handling, outlier clipping, coordinate filtering |
| `featured_data.parquet` | 628,200 | 19 | After feature engineering (11 derived features added) |

The cleaning step removes records outside coordinate bounds (lon > 78°E), reducing from 753,840 to 628,200 rows.

---

## Processed Data (`data/processed/`)

| Split | File | Rows | Columns | Date Range |
|-------|------|------|---------|------------|
| **Training** | `training.csv` | **439,740** | 14 | 1981-01-01 – 2011-02-06 |
| **Validation** | `validation.csv` | **94,230** | 14 | 2011-02-06 – 2017-07-20 |
| **Testing** | `testing.csv` | **94,230** | 14 | 2017-07-20 – 2023-12-31 |
| **Total** | | **628,200** | | |

### Column Overview

All three splits share the same 14 columns:

| # | Column | Type | Role |
|---|--------|------|------|
| 1 | `Date` | string | Temporal index |
| 2 | `Latitude` | float64 | Spatial coordinate |
| 3 | `Longitude` | float64 | Spatial coordinate |
| 4 | `Rainfall` | float64 | Target & Feature |
| 5 | `MaxTemp` | float64 | Target & Feature |
| 6 | `MinTemp` | float64 | Target & Feature |
| 7 | `Month` | int64 | Temporal feature |
| 8 | `Week` | int64 | Temporal feature |
| 9 | `Season` | string | Categorical feature |
| 10 | `Monsoon` | int64 | Binary indicator |
| 11 | `RollingRain7` | float64 | Rolling feature |
| 12 | `RollingRain30` | float64 | Rolling feature |
| 13 | `RollingTemp7` | float64 | Rolling feature |
| 14 | `RollingTemp30` | float64 | Rolling feature |

### Spatial Coverage (Processed)

- **Latitude:** 11.5°N to 18.5°N (8 values)
- **Longitude:** 74.0°E to 78.0°E (5 values)
- **Grid cells:** 40 (reduced from 48 after coordinate filtering)

### Target Variable Statistics (Training Split)

| Variable | Mean | Std | Min | 25% | 50% | 75% | Max |
|----------|------|-----|-----|-----|-----|-----|-----|
| Rainfall (mm) | 3.40 | 7.65 | 0.00 | 0.00 | 0.13 | 2.72 | 45.54 |
| MaxTemp (°C) | 31.35 | 4.38 | 23.06 | 27.99 | 30.27 | 33.94 | 44.07 |
| MinTemp (°C) | 21.07 | 4.20 | 9.39 | 18.46 | 21.31 | 23.84 | 30.01 |

### Split Summary

- **Training:** ~70% of data (1981–2011)
- **Validation:** ~15% of data (2011–2017)
- **Testing:** ~15% of data (2017–2023)

### Feature/Target Count

- **11 feature columns** (excluding Date, Latitude, Longitude): Rainfall, MaxTemp, MinTemp, Month, Week, Season, Monsoon, RollingRain7, RollingRain30, RollingTemp7, RollingTemp30
- **3 target columns:** Rainfall, MaxTemp, MinTemp (note: targets also appear as features, using past values via sliding windows)

### Data Quality

- **Missing values:** None (0 nulls across all splits)
- **Coordinate range:** Karnataka state, India (11.5°–18.5°N, 74.0°–78.0°E)
