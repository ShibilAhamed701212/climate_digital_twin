# Security Report — Climate Digital Twin

## 1. Dependency Vulnerability Analysis

### Runtime Dependencies (from `pyproject.toml`)

| Package | Version Constraint | Known Vulns | Notes |
|---|---|---|---|
| `pandas` | >=2.0 | None in spec | Latest major version |
| `numpy` | >=1.24 | None in spec | Compatible with FAISS (needs pin for NumPy<2) |
| `torch` | >=2.0 | None in spec | PyTorch LTS |
| `pytorch-lightning` | >=2.0 | None in spec | — |
| `scikit-learn` | >=1.3 | None in spec | — |
| `fastapi` | >=0.104 | None in spec | FastAPI latest |
| `streamlit` | >=1.28 | None in spec | Known Starlette compatibility issue |
| `shap` | >=0.43 | None in spec | — |
| `faiss-cpu` | >=1.7 | None in spec | NumPy 2.x compatibility issue |
| `sentence-transformers` | >=2.2 | None in spec | — |
| `httpx` | >=0.25 | None in spec | HTTP client |
| `langchain` | >=0.1 | None in spec | — |
| `langchain-community` | >=0.1 | None in spec | — |

### Development Dependencies

| Package | Version Constraint | Purpose |
|---|---|---|
| `pytest` | >=7.4 | Testing |
| `pytest-cov` | >=4.1 | Coverage |
| `pytest-asyncio` | >=0.23 | Async testing |
| `ruff` | >=0.1 | Linting |
| `black` | >=23.12 | Formatting |
| `isort` | >=5.13 | Import sorting |
| `pre-commit` | >=3.6 | Pre-commit hooks |
| `mypy` | >=1.8 | Type checking |

**Risk:** Dependencies use minimum version constraints (`>=`) rather than exact pins, which could introduce unexpected breaking changes or vulnerabilities on `pip install` in uncontrolled environments. Docker builds mitigate this by capturing known-good versions at build time.

## 2. Authentication & Authorization

### Current State: NO AUTHENTICATION

| Endpoint | Method | Auth Required | Actual |
|---|---|---|---|
| All `/health` endpoints | GET | None | Open |
| All `/state/*` endpoints | GET/POST | None | Open |
| All `/scenarios/*` endpoints | POST/GET/DELETE | None | Open |
| All `/risk/*` endpoints | POST | None | Open |
| `/search` | POST | None | Open |
| `/ask` | POST | None | Open |
| Streamlit Dashboard | GET | None | Open |
| Prometheus | GET | None | Open |
| Grafana | GET | None | Open |

**No API keys, JWT tokens, or session authentication is implemented anywhere in the system.**

## 3. Secrets Management

### Configured Secrets

| Secret | Source | Status |
|---|---|---|
| `OLLAMA_HOST` | `.env` file | Set to `http://ollama:11434` |
| `DOCKER_USERNAME` | GitHub Actions secret | Referenced in `deploy.yml` |
| `DOCKER_PASSWORD` | GitHub Actions secret | Referenced in `deploy.yml` |
| `OLLAMA_API_KEY` | Not configured | **NOT SET** — Ollama runs locally without auth |

### Secrets in Code

| File | Potential Exposure | Risk |
|---|---|---|
| `.env.example` | Shows config template only | Low (no real secrets) |
| `docker-compose.yml` | Environment variables passed to containers | Low (no credentials) |
| `.github/workflows/deploy.yml` | References `secrets.DOCKER_USERNAME`/`DOCKER_PASSWORD` | Low (GitHub-masked) |

### `.gitignore` Coverage

| Pattern | Protects |
|---|---|
| `.env` | Environment secrets |
| `data/external/*` | Raw data |
| `models/checkpoints/*` | Model files |
| `models/exported/*` | Exported models |
| `*.index`, `*.faiss` | Vector store files |
| `.coverage`, `.coverage.*` | Coverage data |
| `logs/*` | Log files |

### `.pre-commit-config.yaml` Security Hooks

| Hook | Protects Against |
|---|---|
| `detect-private-key` | Accidental commit of SSH/private keys |
| `check-json` | Malformed JSON files |
| `check-yaml` | Malformed YAML files |
| `check-toml` | Malformed TOML files |
| `check-added-large-files` | Large file commits (data/model) |
| `trailing-whitespace` | Clean diffs |
| `end-of-file-fixer` | Clean file endings |

## 4. CORS Configuration

### All 6 API Services

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**All services use permissive CORS (`allow_origins=["*"]`).** This is appropriate for a hackathon proof-of-concept where the dashboard and API are accessed from arbitrary origins (e.g., localhost, Docker networks, dev previews). For production deployment, CORS should be restricted to known origins.

## 5. Input Validation

### Pydantic Model Validation

| Endpoint | Validated Fields | Constraints |
|---|---|---|
| `POST /state/sync` | `latitude`, `longitude` | `ge=-90, le=90` and `ge=-180, le=180` |
| `POST /scenarios/simulate` | — | None (all floats) |
| `POST /risk/assess` | — | None (all floats) |
| `POST /risk/heat` | — | None (all floats) |
| `POST /risk/composite` | `score`, `heat_score`, etc. | `ge=0, le=100` |
| `POST /forecast/predict` | — | None (uses defaults) |
| `POST /search` | `query` | Non-null string |
| `POST /ask` | `query` | Non-null string |
| `POST /rollback` | `version_id` | `gt=0` |

**Risk:** Most float fields lack range validation. A user could submit implausible values (e.g., rainfall=1e9), which would propagate through downstream systems.

## 6. Server-Side Validation (Internal)

| Validator | Module | Checks |
|---|---|---|
| Temperature bounds | `simulator/configs/twin_config.yaml` | -10°C to 55°C |
| Rainfall bounds | `simulator/configs/twin_config.yaml` | 0–2000 mm |
| Coordinate bounds | `twin_engine.py` | Karnataka region (11.5–18.5°N, 74.0–78.5°E) |
| Physics | `models/physics.py` | Rainfall >= 0, Tmin <= Tmax, temp [-10, 55] |
| Scenario bounds | `scenario.yaml` | Temperature ±5°C, rainfall -100%/+500% |
| Risk scores | `risk.yaml` | 0–100 range enforced |
| Data pipeline | `pipeline/validate.py` | File existence, columns, date range, lat/lon bounds, value ranges, missing values |

## 7. OWASP Top 10 Checklist (2021)

| # | Category | Status | Notes |
|---|---|---|---|
| A01 | Broken Access Control | ❌ FAIL | No authentication on any endpoint |
| A02 | Cryptographic Failures | ❌ FAIL | No TLS/HTTPS; HTTP-only in Docker |
| A03 | Injection | ⚠️ PARTIAL | Pydantic models validate structure; no SQL injection risk (DuckDB file-based) |
| A04 | Insecure Design | ⚠️ PARTIAL | Permissive CORS; no rate limiting |
| A05 | Security Misconfiguration | ⚠️ PARTIAL | `.gitignore` protects secrets; CORS permissive |
| A06 | Vulnerable Components | ⚠️ PARTIAL | No pinned dependency versions (uses `>=`) |
| A07 | Auth/ID Failures | ❌ FAIL | No identity management |
| A08 | Data Integrity Failures | ✅ PASS | Immutable versioning; pre-commit hooks |
| A09 | Logging & Monitoring | ⚠️ PARTIAL | Health checks implemented; no security-specific logging |
| A10 | SSRF | ✅ PASS | No server-side request forgery vectors (except NASA POWER download) |

**OWASP Score: 3/10 (Critical)**

## 8. Environment-Specific Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Dependency version conflicts (FAISS/NumPy, Streamlit/Starlette) | High | Docker containerization provides reproducible environments |
| Ollama API key not configured | Medium | Ollama runs locally without auth (LAN accessible) |
| Default Grafana credentials (admin/admin) | High | Should be changed on first login |
| Prometheus exposed on 9090 without auth | Medium | Accessible only within Docker network by default |
| No TLS in Docker Compose | High | All traffic is plain HTTP; should use reverse proxy with TLS |

## 9. Recommendations

| Priority | Recommendation | Effort |
|---|---|---|
| **Critical** | Add API key authentication (e.g., `api-key` header middleware) to all FastAPI services | 1 day |
| **High** | Add TLS termination at the Nginx reverse proxy | 1 day |
| **High** | Pin exact dependency versions in `pyproject.toml` and Dockerfiles | 2 hours |
| **High** | Change default Grafana credentials | 10 min |
| **Medium** | Restrict CORS to known origins in production configs | 1 hour |
| **Medium** | Add input range validation for all float fields in Pydantic models | 2 hours |
| **Medium** | Add rate limiting middleware to API Gateway | 1 hour |
| **Low** | Add security headers (X-Content-Type-Options, CSP, etc.) to Nginx config | 30 min |
| **Low** | Configure `pyproject.toml` with `[project.urls]` for vulnerability reporting | 10 min |
| **Low** | Add security audit step to CI pipeline (e.g., `pip-audit` or `safety`) | 1 hour |
