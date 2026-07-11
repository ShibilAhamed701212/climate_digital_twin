# Dataset Report

> **⚠️ ALL DATA IS SYNTHETIC.** Generated with `np.random.seed(42)`.  
> No real climate observations from NASA POWER, IMD, or ISRO have ever been ingested.  
> The pipeline architecture supports real data ingestion but it has never been tested end-to-end.

---

## Data Source (Declared vs Actual)

| Aspect | Declared | Actual |
|--------|----------|--------|
| Source | NASA POWER API (1981–2023) | Synthetic random values with `np.random.seed(42)` |
| Coverage | Karnataka, 48 grid cells | 15 hardcoded districts with synthetic coordinates |
| Resolution | 0.25°–1.0° | Not applicable (synthetic) |
| Time period | 43 years | Synthetic timestamps |
| Total rows | 628,200 | 628,200 synthetic rows generated |

---

## Data Pipeline

| Stage | Implementation | Honest Status |
|-------|---------------|---------------|
| Download | API client with synthetic fallback | ⚠️ Falls back to synthetic on ANY error |
| Validate | Schema + bounds validation | ✅ Validates synthetic data structure |
| Clean | Missing value handling | ✅ Synthetic data has 0 missing values |
| Feature Engineering | 12 engineered features | ✅ Applied to synthetic data |
| Export | Parquet with snappy | ✅ Output format correct |

---

## Data Split (70/15/15 Temporal)

| Split | Rows | Purpose |
|-------|------|---------|
| Train | ~439,740 | Model training (on synthetic data) |
| Validation | ~94,230 | Hyperparameter tuning (on synthetic data) |
| Test | ~94,230 | Final evaluation (on synthetic data) |

---

## Feature Engineering

### Temporal Features
- Year, Month, Day, DayOfYear, Season (derived from synthetic dates)

### Rolling Statistics
- RollingMean_7d, RollingMean_30d (windowed averages of synthetic values)

### Trend Features
- Month-over-month differences (synthetic)

### Prior Rainfall
- Previous day, previous week accumulation (synthetic)

---

## Data Quality Metrics (On Synthetic Data)

| Metric | Value | Meaning |
|--------|-------|---------|
| Missing values | 0 | Expected for generated data |
| Out-of-bounds | 0 | PhysicsValidator passes synthetic values |
| Validated rows | 628,200 | All synthetic data passes schema |
| Quality score | 100% | On synthetic data only |

---

## Storage

| Format | Location | Size |
|--------|----------|------|
| Parquet (snappy) | `data/raw/` | ~15 MB synthetic |
| Parquet (snappy) | `data/processed/` | ~15 MB synthetic |
| CSV (export) | `data/` | ~20 MB synthetic |

---

## Critical Honesty Note

The data pipeline was designed to download from NASA POWER API. The code for this exists. However, every external call is wrapped in:

```python
try:
    result = real_api_call(...)
except:
    result = synthetic_fallback(...)
```

The synthetic fallback is the only path that has ever executed in practice. The real API integration has never been tested against a live endpoint.
