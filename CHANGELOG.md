# Changelog

All notable changes to the **Climate Digital Twin** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0-rc.1] - 2026-08-15

### Added
- Optional `DIE_API_KEY` on the Disaster Intelligence origin (health/metrics remain public).
- Prometheus counters for DIE uploads, assessments, and data-directory writability.
- Gateway SSE proxy for `/disaster/jobs/{id}/stream` (chunked, no full-body buffer).
- Optional Redis-backed gateway rate limits (`RATE_LIMIT_REDIS_URL`) with in-memory fallback.
- Unique OpenAPI operation IDs for the disaster proxy methods.
- SAR speckle median preprocess; STAC collection allowlist; auxiliary DEM/population rasters excluded from flood pairing.
- STAC `links.rel=next` pagination, CDSE/Earthdata/Sentinel Hub auth clients, NASA CMR provider switch, WorldPop/NASADEM URL helpers.
- `GET /disaster/integrations` credential-status and public catalog URLs.
- Learned flood model ids (`unet`, `segformer`, `mask2former`, `changeformer`) registered without bundled weights.
- CDSE/Sentinel Hub token cache with expiry; STAC Range resume downloads; SAR-first scene ranking; Planetary Computer STAC provider.
- Framework disaster types (wildfire, heatwave, drought) with 501 unless `FEATURE_NON_FLOOD`; unknown types 400.
- Optional ClamAV upload scan, DIE storage quota, DIE security headers, RAG category/source filters.
- Assessment reports as markdown/PDF/JSON/CSV; GeoJSON simplification; job listing; duplicate-scene ingest; parallel STAC downloads; GPU compose overlay.
- STAC failover adapter, weight-file discovery, safe zip extract, raster stats/nodata helpers, optional DIE origin allowlist, job `status` filter, GeoJSON assessment export.

### Changed
- Package, gateway, and sidecar health endpoints report **2.1.0**.
- Per-location `flood_area_km2` is polygon area × inundation fraction (not global water pixels × fraction).
- Hospitals in water are assigned by geometry containment, not the first flooded zone.
- GeoJSON `bbox` filters polygons and lines by envelope, not only Point features.
- DIE TIFF decoder/encoder reject oversized or truncated IFDs before allocating pixel arrays.
- Raster/vector stores reject path-traversal names; layer downloads are allowlisted.
- Disaster engine Compose bind is `127.0.0.1:8008` (prod overlay still publishes no host ports).
- CI test matrix is Python 3.11–3.12 (`requires-python = ">=3.11"`).
- Default `limits.max_pixels` is 16e6 to match the in-memory uint8 decoder.

### Fixed
- Gateway `/health` version now follows `GatewayConfig.app_version` instead of a hardcoded string.
- Rate-limiter store prunes expired IP buckets above 10k keys.

---

## [2.0.0] - 2026-08-14

### Added
- Disaster Intelligence Engine (`disaster_intelligence/`) as Compose profile `disaster` on port 8008.
- Gateway reverse-proxy `/disaster/*`, optional health (does not degrade climate `/health`).
- Twin overlay pointer store (`POST /overlay-pointer`) without changing climate TwinState schema.
- Dashboard page 11, Copilot `disaster_intelligence` tool, RAG disaster collection, disaster report type.
- Risk metadata fusion behind `RISK_DIE_FUSION` (scores unchanged by default).
- Scenario type `post_disaster_recovery`.
- Raster preprocess (QC, SAR identity, tiles, gzip GeoJSON sidecars), file-drop ingest, calculated threshold-boundary confidence (no fabricated 0.7 scores).

---

## [1.0.1] - 2026-08-14

### Fixed
- NASA POWER ingest: accept `intent`, merge daily parameters, request RH/pressure/wind, skip fill values; do not fabricate RH=50 / P=1013 / wind=5.
- Twin observations preserve caller `data_source` instead of overwriting with IMD.
- Scenario engine mounts `twin_data` and reloads twin state before simulate.
- Forecast `/forecast/predict` reports the loaded model, not the request default `transformer`.
- Forecast confidence intervals are physics-clamped (no negative rainfall).
- Monte Carlo maps `temperature_2m` onto `temperature_delta` and computes Pearson sensitivity when samples are stored.
- Flood scoring uses same-day rainfall as a 1-day window when accumulation is omitted (not `rainfall * 0.6`).
- Copilot RiskClient maps nested `heat_risk.score` payloads; forecast client falls back to the forecast engine; humidity is no longer invented from rainfall.
- Gateway `/health` probes sidecars when health URLs are configured.
- Gateway image installs `aiohttp` (required by Open-Meteo ingest import path).
- Gateway and copilot Docker healthchecks use `/health/live` so sidecar/LLM probes do not block liveness.
- Gateway sidecar probe timeout is 2s; copilot probe targets `/health/live`.
- Prometheus healthcheck unblocks Grafana `service_healthy`.
- Dashboard default confidence is no longer 0.85; forecast/history fall back to sidecars.

### Changed
- Explainability docs: attributions are deterministic rule contributions serialized in the existing SHAPExplanation schema (not KernelSHAP).
- Dashboard compose port default is 8501.

---

### Added
- Automated dataset download and synthetic data generator script (`scripts/download_data.py`, `make download-data`).
- Integrated secret scanning via Gitleaks and `detect-secrets` into GitHub Actions CI workflow.
- Added comprehensive Open Source governance files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`.
- Added real Codecov coverage XML reporting and README coverage badge integration.

### Changed
- Refactored internal slang (`bhai`) modules to canonical production names: `twin_config.py` and `twin_state_manager.py`.
- Reorganized Streamlit dashboard page numbering (`08_knowledge_base`, `09_spatial_grid`, `10_feedback`).
- Hardened security by replacing real CDS API key UUIDs with standard placeholders (`your-cds-api-key`).

### Removed
- Untracked raw datasets (NetCDF `.nc`, Parquet `.parquet`, CSV) and binary vector indexes (`metadata.pkl`) from Git index.
- Removed legacy test exclusion filters (`-k "not ..."`) from CI workflow.

### Fixed
- Fixed 202+ Ruff linter errors across all packages and test suites.
- Fixed 100% of unit and integration test suite failures.
- Fixed Docker Compose syntax and version warnings.
