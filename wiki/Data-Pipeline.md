# Data Pipeline

## Overview

The **Data Pipeline** (`pipeline/`) ingests, cleans, validates, transforms, and exports hydro-meteorological observations from multiple remote and national data providers into the Climate Digital Twin platform.

---

## Data Providers (`pipeline/providers/`)

| Provider | Source | Frequency | Primary Variables | Status |
|---|---|---|---|---|
| **Open-Meteo API** | ECMWF / ERA5 Seamless | Hourly / Daily | Temperature, Precipitation, Humidity, Wind | Active |
| **NASA POWER** | Satellite Agro-climatology | Daily | Solar Radiation, Precipitation, Temp Max/Min | Active |
| **IMD** | India Meteorological Dept | Daily / Monthly | Station Rainfall, Max/Min Temperature | Configurable |
| **ERA5 Reanalysis** | Copernicus Climate Data Store | Hourly | Global Gridded Climate Reanalysis | Offline / Seed |

---

## Pipeline Architecture & Data Flow

```
External API Ingestion ──► Cleaning & Normalization ──► Validation Rules ──► Feature Engineering
   (Open-Meteo, NASA)        (Unit Conversions)         (Outlier Check)      (Lags, Rolling Means)
                                                                                  │
                                                                                  ▼
                                                                        Parquet Store / Twin
```

---

## Processing Steps

### 1. Ingestion & Normalization (`pipeline/ingest.py`, `clean.py`)
- Standardizes diverse provider schemas into unified internal metrics (`max_temp` in °C, `rainfall` in mm).
- Converts timestamps to UTC ISO-8601 format.

### 2. Validation Engine (`pipeline/validate.py`)
Applies quality rules before observations enter the active state:
- Range validation (e.g., $-20^\circ C \le T \le 60^\circ C$).
- Outlier detection via rolling z-scores.
- Missing value imputation (linear interpolation / climatological mean fallback).
- Rejects non-compliant records to `data/real/rejected/`.

### 3. Feature Engineering (`pipeline/feature_engine.py`)
Generates 40+ dynamic features for ML forecasting models:
- **Lag Features**: 1-day, 3-day, 7-day, 14-day, 30-day historical lags.
- **Rolling Statistics**: 7-day and 30-day moving averages, standard deviations, min, max.
- **Aggregations**: Cumulative precipitation, consecutive dry days, heatwave indices.

---

## Running the Pipeline

```bash
# Execute standard pipeline run
python pipeline/run_pipeline.py

# Download ERA5 climate reanalysis data for India
python scripts/download_era5_india.py

# Verify ERA5 data integrity
python scripts/verify_era5_india.py
```
