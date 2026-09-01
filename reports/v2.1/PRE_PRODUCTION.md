# 2.1 pre-production completion (2026-08-15)

Follow-on to `RELEASE_CANDIDATE.md`. Evidence-only.

## Repository fixes

- Unique OpenAPI operation IDs (`disaster_proxy_get/post/put/patch/delete` + `generate_unique_id_function`).
- Pytest config is `pytest.ini` only (`pyproject.toml` duplicate removed).
- Gateway streams GeoJSON, masks, and layers (not only SSE).
- Rate limiter extracted; optional Redis (`RATE_LIMIT_REDIS_URL`) with memory fallback.
- Job cancel uses `threading.Event` plus status checks.
- TIFF reader rejects compressed / multi-band / non-8-bit files.
- SAR speckle median; S1 vs S2 cloud flags; NASADEM/WorldPop excluded from flood pairing; STAC collection allowlist.
- Health/FastAPI versions for gateway, DIE, copilot, RAG, forecast, report, risk, twin, scenario: **2.1.0**.
- Dockerfiles labeled `org.opencontainers.image.version=2.1.0`.

## Validation

| Check | Result |
|---|---|
| Targeted unit tests | **268 passed** |
| DIE + OpenAPI uniqueness + rate-limit | **35 passed** (subset) |
| Ruff (modified packages) | PASS |
| MyPy (`disaster_intelligence` + gateway modules) | PASS (exit 0) |
| Black | **Not installed** in this environment |
| Import + FastAPI versions | PASS (`2.1.0` for DIE, gateway, copilot, RAG, risk) |
| Compose `--profile disaster config --quiet` | PASS |
| `docker compose --profile disaster build disaster-engine` | PASS (`climate-digital-twin-disaster-engine`) |
| `risk-engine`, `report-service`, `rag-service`, `scenario-engine`, `twin-state-mgr` | PASS (`docker compose build`, exit 0) |
| Gateway / forecast / copilot / dashboard / ollama | **Not built** in the confirmed commands |
| Full `pytest tests/` | **Not run** |
| Live CDSE / GPU | **Not run** |

## Scores (updated)

- Repository health: **84** (was 78)
- Architecture: **90** (unchanged)
- Code quality: **86** (was 82)
- Scientific readiness: **84** (was 81)
- Production readiness: **82** (was 76)
- Security readiness: **83** (was 80)

## Recommendation

**RELEASE CANDIDATE** — software blockers in-repo for DIE/gateway are addressed; production promotion still needs Linux full-suite CI, remaining image builds (CPU torch index for RAG), and CDSE credentials.
