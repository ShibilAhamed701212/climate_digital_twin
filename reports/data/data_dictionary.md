# Data Dictionary

> Column definitions for the synthetic climate dataset.  
> Schema mirrors NASA POWER API but values are `np.random.seed(42)` generated.

---

## Source Columns

| Column | Type | Description | Source | Synthetic? |
|--------|------|-------------|--------|------------|
| `date` | date | Observation date | Synthetic | ✅ |
| `latitude` | float | Grid cell latitude | Synthetic (15 districts) | ✅ |
| `longitude` | float | Grid cell longitude | Synthetic | ✅ |
| `district` | string | Karnataka district name | Config (15 districts) | ✅ |
| `t2m_max` | float | Max temperature (°C) | Synthetic | ✅ |
| `t2m_min` | float | Min temperature (°C) | Synthetic | ✅ |
| `t2m_mean` | float | Mean temperature (°C) | Synthetic (derived) | ✅ |
| `precipitation` | float | Daily rainfall (mm) | Synthetic | ✅ |
| `rh_mean` | float | Relative humidity (%) | Synthetic | ✅ |
| `wind_speed` | float | Wind speed (m/s) | Synthetic | ✅ |
| `surface_pressure` | float | Surface pressure (kPa) | Synthetic | ✅ |
| `solar_radiation` | float | Solar radiation (MJ/m²) | Synthetic | ✅ |

---

## Engineered Features

| Column | Type | Description | Window |
|--------|------|-------------|--------|
| `year` | int | Year extracted from date | — |
| `month` | int | Month extracted from date | — |
| `day` | int | Day extracted from date | — |
| `day_of_year` | int | Day of year (1–366) | — |
| `season` | string | DJF/MAM/JJA/SON | — |
| `rolling_mean_7d` | float | 7-day rolling mean of target | 7 days |
| `rolling_mean_30d` | float | 30-day rolling mean of target | 30 days |
| `trend_mom` | float | Month-over-month difference | 30 days |
| `precip_prev_day` | float | Previous day precipitation | 1 day |
| `precip_prev_week` | float | Previous week accumulation | 7 days |
| `t2m_max_lag1` | float | Max temp, 1-day lag | 1 day |
| `t2m_min_lag1` | float | Min temp, 1-day lag | 1 day |

---

## Target Variables (Forecasting)

| Target | Description | Distribution (Synthetic) |
|--------|-------------|------------------------|
| `precipitation` | Daily rainfall (mm) | Synthetic uniform |
| `t2m_max` | Max temperature (°C) | Synthetic uniform |
| `t2m_min` | Min temperature (°C) | Synthetic uniform |

---

## Dataset Splits

| Split | Date Range (Synthetic) | Rows |
|-------|----------------------|------|
| Train | 1981-01-01 to 2011-01-01 (simulated) | ~439,740 |
| Validation | 2011-01-02 to 2017-06-30 (simulated) | ~94,230 |
| Test | 2017-07-01 to 2023-12-31 (simulated) | ~94,230 |

---

## Notes

- All values are synthetic. Real climate data from Karnataka would show different distributions, correlations, and seasonal patterns.
- The schema is designed to match NASA POWER API format for future real data ingestion.
- PhysicsValidator rules (rainfall >= 0, t2m_min <= t2m_max) are enforced on synthetic data and pass trivially.
