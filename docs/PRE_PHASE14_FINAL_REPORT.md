# Pre-Phase 14 Final Report — Complete ERA5 Datasets

Date: 2026-08-01
Project: Climate Digital Twin

---

## Executive Summary

Completed Karnataka 2021-2023 (651 cells, 3 years, ~40 MB) and India 2021 (15,609 cells, 1 year, 280 MB) ERA5 datasets. Both verified with zero failures. The resumable download pipeline is operational for expanding India to 2022-2023 and beyond.

---

## Dataset Inventory

### Karnataka 2021-2023

| Property | Value |
|----------|-------|
| Region | 11.0-18.5degN, 74.0-79.0degE |
| Grid | 31 x 21 = 651 cells |
| Resolution | 0.25deg native |
| Years | 2021, 2022, 2023 |
| Months | 36 (all complete) |
| Variables | t2m, d2m, sp, u10, v10, tp, ssrd, strd |
| Timesteps | 6-hourly (00, 06, 12, 18 UTC) |
| Size | ~40 MB |
| Failures | 0 |
| Location | data/validation/era5/karnataka/raw/ |

### India 2021

| Property | Value |
|----------|-------|
| Region | 6.0-38.0degN, 68.0-98.0degE |
| Grid | 129 x 121 = 15,609 cells |
| Resolution | 0.25deg native |
| Years | 2021 |
| Months | 12 (all complete) |
| Variables | t2m, d2m, sp, u10, v10, tp, ssrd, strd |
| Timesteps | 6-hourly (00, 06, 12, 18 UTC) |
| Size | ~280 MB |
| Failures | 0 |
| T2m range | -9.8C (Himalayas) to 38.1C (desert) |
| Location | data/validation/era5/india/raw/ |

---

## Download Performance

| Region | Monthly size | Monthly time | 1 year total |
|--------|-------------|--------------|-------------|
| Karnataka (651 cells) | 1.1 MB | 82s | 17 min |
| India (15,609 cells) | 23 MB | 89s | 18 min |

CDS API performance is consistent regardless of grid size — processing dominates network transfer.

---

## Pipeline Capabilities

| Feature | Status |
|---------|--------|
| Resume/checkpoint | VERIFIED |
| Automatic skip of completed | VERIFIED |
| Manifest tracking | VERIFIED |
| Dry-run mode | VERIFIED |
| Multi-year support | VERIFIED |
| Region selection | VERIFIED |
| CDS rate limit compliance | VERIFIED |

---

## Commands to Continue

```bash
# India 2022-2023 (est. 36 minutes)
python scripts/download_era5_india.py --region india --start-year 2022 --end-year 2023

# India 2000-2023 (est. 7 hours, resumable)
python scripts/download_era5_india.py --region india --start-year 2000 --end-year 2023
```

---

## Test Results

| Suite | Passed |
|-------|--------|
| Phase 7 simulation | 38 |
| Phase 4-6 regressions | 119 |
| Copilot | 21 |
| ERA5 pipeline (all downloads) | 48/48 months, 0 failures |

---

## Storage

```
data/validation/era5/
  karnataka/raw/          # 36 files, ~40 MB
  karnataka/karnataka_manifest.json
  india/raw/              # 12 files, ~280 MB
  india/download_manifest.json
  test_bengaluru_202201.nc
```

---

## Ready for Phase 14

Karnataka 2021-2023 provides a 651-cell, 3-year ERA5 dataset with 8 atmospheric variables at native 0.25deg resolution. This is sufficient for:
- Multi-grid Twin with proper spatial coverage
- Gridded climate intelligence
- Spatial interpolation testing
- Regional hazard assessment

India 2021 provides the foundation for all-India scaling.

---
*Generated: 2026-08-01*
