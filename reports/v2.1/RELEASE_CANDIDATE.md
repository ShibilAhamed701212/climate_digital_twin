# Climate Digital Twin 2.1.0-rc.1 — Release Candidate Report

Date: 2026-08-15  
Scope: Hardening of the frozen V2.1 architecture (no redesign).  
Evidence: targeted unit tests, Ruff, Compose `config`, DIE coverage measurement.

This document is the Phase 11–12 deliverable. It does **not** claim a full-stack live run, GPU inference, CDSE download, or 95% coverage.

---

## 1. Executive Summary

Version **2.1.0-rc.1** hardens the existing Disaster Intelligence Engine and gateway without changing climate TwinState, risk score formulas (unless DIE fusion flags are on), or public route paths.

The highest-impact correctness fix is per-location flood area: it no longer multiplies **global** water pixels by a location’s inundation fraction. Hospitals in water are assigned by polygon containment. TIFF and storage paths reject traversal and oversized IFDs. Gateway `/disaster/.../stream` is chunked. Package/gateway version is aligned to 2.1.0.

**Release recommendation: RELEASE CANDIDATE** (not production-ready). Remaining blockers are external (CDSE, GPU, licensed imagery) plus incomplete full-suite/coverage evidence in this pass.

---

## 2. Repository Health Score: **78 / 100**

Deducted for dual pytest config (`pytest.ini` vs `pyproject.toml`), DIE package coverage at 77%, jobs/STAC paths thinly tested, and no measured end-to-end Docker image rebuild in this session.

---

## 3. Architecture Score: **90 / 100**

Architecture was frozen and preserved: hexagonal DIE, gateway reverse-proxy `/disaster/*`, overlay pointers only, climate `/health` independent of DIE, Compose profile `disaster`.

---

## 4. Code Quality Score: **82 / 100**

Ruff check passed on modified DIE/gateway files. Safe refactors only (path sanitization, decoder bounds, bbox envelopes). OpenAPI still warns about duplicate operation IDs on the catch-all disaster proxy.

---

## 5. Scientific Readiness Score: **81 / 100**

| Topic | Status |
|---|---|
| Flood area per location | PASS — polygon spherical area × sampled inundation fraction |
| Global flood area KPI | Unchanged — water pixels × approximate pixel area |
| Population exposed | Unchanged — `population * flood_fraction` when population present; else flagged |
| Road length | Haversine; `None` if geometry invalid |
| Hospital assignment | PASS — point-in-polygon vs location features (was first flooded zone) |
| Confidence | Unchanged — threshold boundary confidence; no default 0.7 |
| Economic loss | Still not invented unless experimental flag (value remains `None`) |
| Forecast / twin climate | Not re-run this pass |

---

## 6. Production Readiness Score: **76 / 100**

Compose disaster profile `config --quiet` **PASS** (exit 0). DIE image still non-root, healthcheck on `/health/live`, `stop_grace_period` 20s, host bind `127.0.0.1:8008`. Prod overlay still `ports: []` + read-only. Full image **build** not executed here.

---

## 7. Security Readiness Score: **80 / 100**

| Control | Status |
|---|---|
| TIFF magic + size + IFD bounds | PASS (unit) |
| Path traversal on raster/vector names | PASS (unit) |
| Layer allowlist on download | PASS (unit) |
| Optional `DIE_API_KEY` | PASS (unit) |
| Compose localhost bind | PASS (compose test + config) |
| Gateway rate-limit prune | Implemented; not load-tested |
| pip-audit / bandit this session | **Not run** |
| GDAL JPEG2000 skip | Unchanged env defaults |

---

## 8. Performance Summary

| Change | Expected effect | Measured? |
|---|---|---|
| SSE proxy `aiter_bytes` | Avoid buffering long job streams | Unit mock only |
| TIFF dim/pixel caps | Prevent decoder OOM | Unit reject of 9000² tags |
| `max_pixels` 16e6 | Align QC with in-memory decoder | Config change |
| Rate-limit eviction | Bound memory | Not load-tested |

No throughput/latency benchmark numbers were collected. None are claimed.

---

## 9. Validation Summary

| Check | Result |
|---|---|
| DIE unit tests | **25 passed** (`tests/unit/disaster_intelligence/test_engine.py`) |
| Gateway disaster proxy | **3 passed** (502, forward, SSE stream mock) |
| Gateway main/health/config | **Passed** after version + patch-site fixes |
| Copilot disaster + DIE fusion + overlay store + post-disaster scenario | **Passed** (targeted files) |
| Compose `docker compose --profile disaster config --quiet` | **PASS** (exit 0) |
| Ruff on modified DIE/gateway | **PASS** |
| Targeted API/DIE/docker/copilot/risk fusion | **222 passed** in 56.69s |
| Live CDSE / GPU / dashboard browser | **Blocked / not run** |

---

## 10. Testing Summary

- DIE package coverage (DIE tests only, `--cov=disaster_intelligence`): **77%** (1900 stmts, 435 miss). Not 95%.
- Weakest DIE modules: `adapters/stac/cdse.py` 27%, `application/jobs.py` 52% (thread/create path), `application/ingest.py` STAC branch 59%.
- `pytest.ini` still enforces `--cov-fail-under=80` on a **union** of packages; `pyproject.toml` pytest config is ignored when `pytest.ini` is present.
- CI matrix corrected to **3.11 and 3.12** (3.10 contradicted `requires-python = ">=3.11"`).

---

## 11. Docker Summary

- `Dockerfile.disaster`: `PYTHONUNBUFFERED=1`, `STOPSIGNAL SIGTERM`, non-root user unchanged.
- Compose: `127.0.0.1:${DISASTER_PORT:-8008}:8008`, `DIE_API_KEY`, `stop_grace_period: 20s`.
- Prod overlay: no published ports, read-only, `no-new-privileges` (existing tests still pass).
- Image rebuild/push: **not run**.

---

## 12. Documentation Summary

Updated: `CHANGELOG.md` (2.1.0-rc.1), `README.md` (version badge, `/disaster`, 11 dashboard pages), `wiki/Configuration-Reference.md`, `wiki/API-Reference.md` health version, `wiki/Developer-Guide.md`, `wiki/Deployment-Guide.md`, `wiki/Troubleshooting.md`, `wiki/Disaster-Intelligence-Engine.md`, `.env.example` (`DIE_API_KEY`, `CDSE_PASSWORD` preserved).

---

## 13. Remaining External Blockers

- CDSE username/password and allowlisted download hosts for live Sentinel rasters.
- GPU / commercial flood models (`MODEL_FLOOD` beyond threshold).
- Licensed imagery and full Karnataka OSM freshness.
- Internet-dependent STAC search in CI.
- Windows torch C++ coverage gap (pre-existing; documented in `pyproject.toml`).

---

## 14. Remaining Technical Debt

- Catch-all gateway proxy OpenAPI duplicate operation IDs.
- Dual pytest configuration files.
- In-memory uint8 TIFF (not COG/rasterio GeoTIFF geotransform); AOI clip is identity.
- In-process rate limiter (not Redis).
- Job worker is a daemon thread; cancel is cooperative between stages.
- STAC and job-thread coverage.
- Non-stream GeoJSON still fully buffered through the gateway.

---

## 15. Recommended Future Improvements (Version 3.0 only)

- Rasterio/GDAL COG reader with CRS/geotransform clip (keep threshold model as fallback).
- Redis-backed rate limits and job queue.
- Unique OpenAPI operation IDs or typed DIE routes on the gateway.
- Single pytest config source.
- Optional learned flood models behind the existing factory (no silent score invention).

---

## 16. Release Recommendation

**RELEASE CANDIDATE**

Use 2.1.0-rc.1 for staging. Promote to production only after: full `pytest tests/` on Linux CI, DIE image build, CDSE dry-run with real credentials in a private environment, and pip-audit/bandit on the lock set.

---

## Improvement log (evidence)

### Issue 1 — Per-location flood area overstated
- **Root cause:** `zonal_stats` used `global_water_pixels * pixel_area * location_fraction`.
- **Files:** `disaster_intelligence/domain/zonal.py`, `disaster_intelligence/domain/geometry.py`
- **Functions:** `zonal_stats`, `polygon_area_km2`, `_rings_from_geom`
- **Reason:** Location flood area must be that location’s geometry, not the whole mask.
- **Validation:** `TestHardening.test_zonal_area_uses_polygon_not_global_mask` PASS
- **Regression:** DIE API job path still asserts `flood_area_km2` present PASS

### Issue 2 — Hospitals assigned to first flooded zone
- **Root cause:** First zonal row with `flood_fraction > 0` received every hospital.
- **Files:** `disaster_intelligence/application/assessment.py`, `disaster_intelligence/api/main.py`, `disaster_intelligence/domain/zonal.py`
- **Functions:** `location_id_containing`, `run_assessment`, `relief_plan`
- **Reason:** Relief ranking must follow geometry.
- **Validation:** unit path via existing assessment job; containment helper covered indirectly
- **Regression:** PASS

### Issue 3 — GeoJSON bbox ignored non-Point features
- **Root cause:** Filter returned `True` for polygons.
- **Files:** `disaster_intelligence/api/main.py`, `disaster_intelligence/domain/geometry.py`
- **Functions:** `geometry_envelope`, `envelope_intersects_bbox`, `get_geojson`
- **Validation:** `test_bbox_filters_polygons` PASS
- **Regression:** PASS

### Issue 4 — TIFF / path traversal
- **Root cause:** IFD dimensions unbounded; storage names joined unsanitized.
- **Files:** `geotiff.py`, `paths.py`, `raster_store.py`, `vector_store.py`
- **Validation:** `test_tiff_rejects_oversized_tags`, `test_safe_storage_rejects_paths`, `test_unknown_layer_rejected` PASS
- **Regression:** PASS

### Issue 5 — SSE buffered at gateway
- **Root cause:** Proxy always read `resp.content`.
- **Files:** `backend/api/routes/disaster.py`
- **Functions:** `_proxy`
- **Validation:** `test_disaster_proxy_streams_sse` PASS (mock)
- **Regression:** `test_disaster_proxy_forwards_ok` PASS

### Issue 6 — Version / CI mismatch
- **Root cause:** Changelog 2.0 vs pyproject 0.1.0; health hardcoded; CI included 3.10.
- **Files:** `pyproject.toml`, `backend/api/config.py`, `backend/api/routes/health.py`, `.github/workflows/ci.yml`, tests
- **Validation:** health/config tests PASS; Compose config PASS
- **Regression:** PASS

### Issue 7 — Origin exposure / optional DIE auth
- **Root cause:** DIE published on all interfaces; no origin API key.
- **Files:** `docker-compose.yml`, `disaster_intelligence/api/main.py`
- **Validation:** compose unit asserts `127.0.0.1`; `test_api_key_protects_die` PASS
- **Regression:** PASS
