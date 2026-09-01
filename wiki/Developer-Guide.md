# Developer Guide

## Layout

- Climate services remain under `backend/`, `simulator/`, `risk/`, `copilot/`, `dashboard/`.
- Disaster Intelligence is a separate package `disaster_intelligence/` (hexagonal: `domain`, `ports`, `adapters`, `application`, `api`).
- The gateway reverse-proxies `/disaster/*`. Do not import GDAL or DIE domain into the gateway.

## Local DIE

```bash
set DISASTER_DATA_DIR=data/disaster
set TWIN_POINTER_ENABLED=false
uvicorn disaster_intelligence.api.main:app --port 8008
```

If `DIE_API_KEY` is set, send `Authorization: Bearer <key>` to origin `:8008` (not required for `/health` or `/metrics`).

Tests: `python -m pytest tests/unit/disaster_intelligence tests/unit/docker/test_compose_disaster.py -q`

## Contracts

Twin climate parquet schema is frozen. DIE is system of record for assessments. Twin stores overlay pointers only (`POST /overlay-pointer` on `:8001`).
