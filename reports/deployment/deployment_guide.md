# Deployment Guide — Climate Digital Twin

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker | 20.10+ | `docker --version` to verify |
| Docker Compose | 2.x+ | `docker compose version` to verify |
| Python | 3.10+ | For local development only |
| Ollama | latest | Required for Copilot LLM; pulled automatically as Docker service |

## 1. Environment Setup

### 1.1 Clone the Repository

```bash
git clone <repo-url> climate-digital-twin
cd climate-digital-twin
```

### 1.2 Create Environment File

```bash
cp deployment/configs/.env.example .env
```

The `.env.example` file defines 14 environment variables:

| Variable | Default | Description |
|---|---|---|
| `TWIN_STATE_MGR_PORT` | 8001 | Twin State Manager port |
| `FORECAST_PORT` | 8006 | Forecast Engine port |
| `SCENARIO_PORT` | 8002 | Scenario Engine port |
| `RISK_PORT` | 8003 | Risk Engine port |
| `RAG_PORT` | 8004 | RAG Service port |
| `COPILOT_PORT` | 8005 | Copilot Agent port |
| `GATEWAY_PORT` | 8000 | API Gateway port |
| `DASHBOARD_PORT` | 8501 | Streamlit Dashboard port |
| `LLM_MODEL` | qwen3:8b | Ollama model for Copilot |
| `LLM_TEMPERATURE` | 0.1 | LLM sampling temperature |
| `OLLAMA_HOST` | http://ollama:11434 | Ollama service URL |
| `DATA_DIR` | /app/data | Data directory (container) |
| `MODEL_DIR` | /app/models | Model directory (container) |
| `VECTOR_STORE_DIR` | /app/knowledge/vector_store | Vector store directory (container) |
| `LOG_DIR` | /app/logs | Log directory (container) |
| `DEMO_MODE` | synthetic | Data mode (synthetic or live) |

## 2. Startup Sequence

### Quick Start (Recommended)

```bash
make up
```

This runs:
1. `docker compose up --build -d` — builds and starts all 11 services
2. Waits 10 seconds for services to initialize
3. Runs Python health check against all 8 application services
4. Prints dashboard URL: `http://localhost:8501`

### Manual Startup

```bash
# Build images
docker compose build

# Start all services in detached mode
docker compose up -d

# Verify health
python deployment/health/health_check.py
```

### Startup Order (Dependency Chain)

```
twin-state-mgr ─┬─→ scenario-engine ──→ copilot-agent ──→ fastapi-gateway ──→ streamlit-dashboard
                ├─→ risk-engine ───────┘
                └─→ forecast-engine ───┘
                rag-service ───────────┘
                ollama ─────────────────┘
```

The dependency chain is enforced via Docker Compose `depends_on` with `condition: service_healthy` (or `service_started` for non-blocking dependencies).

### Including Monitoring

```bash
# Start with monitoring profile
docker compose --profile monitoring up -d
```

Or use the standalone monitoring overlay:

```bash
docker compose -f deployment/compose/monitoring.yml up -d
```

## 3. Health Checks

### All 8 Application Services

| Service | Health Endpoint | Expected Response |
|---|---|---|
| fastapi-gateway | `GET http://localhost:8000/health` | `{"status":"healthy","service":"fastapi-gateway","version":"1.0.0"}` |
| twin-state-mgr | `GET http://localhost:8001/health` | `{"status":"healthy","service":"twin-state-mgr","version":"1.0.0"}` |
| scenario-engine | `GET http://localhost:8002/health` | `{"status":"healthy","service":"scenario-engine","version":"1.0.0"}` |
| risk-engine | `GET http://localhost:8003/health` | `{"status":"healthy","service":"risk-engine","version":"1.0.0"}` |
| rag-service | `GET http://localhost:8004/health` | `{"status":"healthy","service":"rag-service","version":"1.0.0"}` |
| copilot-agent | `GET http://localhost:8005/health` | `{"status":"healthy","service":"copilot-agent","version":"1.0.0","ollama":{...},"tools":{...}}` |
| forecast-engine | `GET http://localhost:8006/health` | `{"status":"healthy","service":"forecast-engine","version":"1.0.0"}` |
| streamlit-dashboard | `GET http://localhost:8501` | HTTP 200 (HTML page) |

### Health Check Scripts

```bash
# Shell script (requires curl)
bash deployment/scripts/health_check.sh

# Python script (requires urllib)
python deployment/health/health_check.py
```

The Python health check script (`deployment/health/health_check.py`) queries all 8 services with a 5-second timeout per request and exits with code 1 if any service is unhealthy.

## 4. Shutdown

```bash
make down
# Or
bash deployment/scripts/shutdown.sh
```

Both run `docker compose down`, stopping all services and removing containers while preserving named volumes.

## 5. Monitoring Setup

### Prometheus
- URL: `http://localhost:9090`
- Scrapes all 7 application services every 15 seconds
- Config: `deployment/monitoring/prometheus.yml`
- Available metrics: `up` (service health), `http_requests_total`, etc. (via FastAPI Prometheus instrumentation)

### Grafana
- URL: `http://localhost:3000`
- Default login: admin/admin (change on first login)
- Pre-configured data source: Prometheus
- Pre-loaded dashboard: "Service Health" with 6 stat panels
- Config files:
  - `deployment/monitoring/grafana/datasources/datasource.yml`
  - `deployment/monitoring/grafana/dashboard.yml`
  - `deployment/monitoring/grafana/dashboards/service-health.json`

### Nginx Reverse Proxy
Config at `deployment/configs/nginx.conf`:
- Routes `/api/` → `fastapi-gateway:8000`
- Routes `/` → `streamlit-dashboard:8501`
- WebSocket support for Streamlit (`Upgrade`/`Connection` headers)

## 6. CI/CD Pipeline

### Continuous Integration (`.github/workflows/ci.yml`)

| Stage | Tool | Python Versions |
|---|---|---|
| Lint | ruff | 3.12 |
| Test | pytest | 3.10, 3.12 |
| Docker Build | Docker Buildx | — |

### Continuous Deployment (`.github/workflows/deploy.yml`)

Triggered by version tags (`v*`). Workflow:
1. Log in to Docker Hub (`DOCKER_USERNAME`/`DOCKER_PASSWORD` secrets)
2. Build all images via `docker compose build`
3. Push all images via `docker compose push`

### Makefile Targets

| Target | Command | Description |
|---|---|---|
| `make install` | `pip install -e ".[dev]"` | Install Python dependencies |
| `make test` | `pytest tests/ -v` | Run all tests |
| `make lint` | `ruff check .` | Run linter |
| `make pipeline` | `python pipeline/run_pipeline.py` | Run data pipeline |
| `make train` | `python models/run_forecast.py` | Train forecasting models |
| `make dashboard` | `streamlit run dashboard/app.py` | Launch dashboard locally |
| `make docker` | `docker compose build` | Build Docker images |
| `make up` | `docker compose up --build -d` | Start all services |
| `make down` | `docker compose down` | Stop all services |
| `make demo` | `bash deployment/scripts/demo.sh` | Full demo walkthrough |
| `make clean` | `rm -rf .pytest_cache .ruff_cache __pycache__` | Clean temporary files |

## 7. Demo Mode

### One-Click Demo

```bash
bash deployment/scripts/demo.sh
```

This runs a 6-step walkthrough:
1. **Start all services** — `docker compose up --build -d`
2. **Wait for readiness** — 15 seconds
3. **Verify health** — Python health check
4. **Open Dashboard** — `http://localhost:8501`
5. **Try Forecast Viewer** — 7-day predictions
6. **Use Scenario Simulator** — What-if analysis
7. **Explore Climate Risk** — SHAP explanations
8. **Ask Copilot** — Natural-language queries
9. **Generate Reports** — Insights & reports page

### Synthetic Data Fallback

All services include synthetic data fallback for offline environments:
- Pre-cached model predictions (deterministic)
- Synthetic climate data generation (NASA POWER structure)
- Dummy FAISS embeddings (hash-based, 384-dim)
- Deterministic SHAP estimation
- No external API dependencies required

## 8. Local Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run linter
make lint

# Launch dashboard with synthetic data
make dashboard
```

## 9. Architecture

See `deployment/docs/architecture.md` for full architecture documentation with:
- ASCII architecture diagram
- Service descriptions (all 9 services)
- Data flow (8 steps)
- Technology stack (PyTorch, FastAPI, Streamlit, FAISS, Ollama)
- Offline demo mode description
