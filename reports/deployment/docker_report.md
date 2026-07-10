# Docker Report — Climate Digital Twin

## 1. Dockerfiles

All 8 service Dockerfiles use `python:3.10-slim` as the base image and include HEALTHCHECK instructions with pinned dependency versions.

| Dockerfile | Service | Base Image | Build Stage | Exposed Port | CMD Entrypoint | Key Dependencies |
|---|---|---|---|---|---|---|
| `Dockerfile.twin_state_mgr` | twin-state-mgr | python:3.10-slim | single-stage | 8001 | `uvicorn simulator.api.main:app` | fastapi, uvicorn, pydantic, pyyaml, pandas, numpy, duckdb |
| `Dockerfile.forecast` | forecast-engine | python:3.10-slim | builder (gcc) | 8006 | `uvicorn backend.services.forecast.main:app` | torch, pandas, numpy, scikit-learn |
| `Dockerfile.scenario` | scenario-engine | python:3.10-slim | single-stage | 8002 | `uvicorn simulator.scenarios.api:app` | fastapi, uvicorn, pydantic, pyyaml, pandas, numpy |
| `Dockerfile.risk` | risk-engine | python:3.10-slim | builder (gcc) | 8003 | `uvicorn risk.api.main:app` | fastapi, uvicorn, pydantic, pyyaml, shap, pandas, numpy, scikit-learn |
| `Dockerfile.rag` | rag-service | python:3.10-slim | single-stage | 8004 | `uvicorn knowledge.api.main:app` | fastapi, uvicorn, pydantic, pyyaml, sentence-transformers, faiss-cpu |
| `Dockerfile.copilot` | copilot-agent | python:3.10-slim | single-stage | 8005 | `uvicorn copilot.api.main:app` | fastapi, uvicorn, pydantic, pyyaml, httpx |
| `Dockerfile.gateway` | fastapi-gateway | python:3.10-slim | builder | 8000 | `uvicorn backend.api.main:app` | fastapi, uvicorn, pydantic, pyyaml, httpx |
| `Dockerfile.dashboard` | streamlit-dashboard | python:3.10-slim | single-stage | 8501 | `streamlit run dashboard/app.py` | streamlit, plotly, folium, streamlit-folium, pandas, numpy, requests |

### Build Notes
- **Builder stage** (forecast, risk, gateway): Uses `gcc` for compiling native extensions during `pip install`, then discards build tools (single-stage pattern in the remaining layers).
- **Volumes** declared in Dockerfiles:
  - `Dockerfile.forecast`: `/app/models/checkpoints`, `/app/models/exported`, `/app/models/evaluation`
  - `Dockerfile.rag`: `/app/knowledge/vector_store`

## 2. Docker Compose Services

`docker-compose.yml` (version 3.8) defines 11 services: 8 application services + Ollama + 2 monitoring services.

### Service Table

| Service | Build Context | Dockerfile | Port (host:container) | Depends On (condition) | Volumes | Networks |
|---|---|---|---|---|---|---|
| **twin-state-mgr** | . | `Dockerfile.twin_state_mgr` | `${TWIN_STATE_MGR_PORT:-8001}:8001` | — | `twin_data:/app/data`, `./simulator/configs:/app/simulator/configs` | twin_network |
| **forecast-engine** | . | `Dockerfile.forecast` | `${FORECAST_PORT:-8006}:8006` | twin-state-mgr (service_started) | `model_data:/app/models` | twin_network |
| **scenario-engine** | . | `Dockerfile.scenario` | `${SCENARIO_PORT:-8002}:8002` | twin-state-mgr (service_healthy) | `./simulator/configs:/app/simulator/configs` | twin_network |
| **risk-engine** | . | `Dockerfile.risk` | `${RISK_PORT:-8003}:8003` | twin-state-mgr (service_healthy) | — | twin_network |
| **rag-service** | . | `Dockerfile.rag` | `${RAG_PORT:-8004}:8004` | — | `vector_store:/app/knowledge/vector_store` | twin_network |
| **ollama** | `ollama/ollama:latest` | — | `11434:11434` | — | `ollama_data:/root/.ollama` | twin_network |
| **copilot-agent** | . | `Dockerfile.copilot` | `${COPILOT_PORT:-8005}:8005` | ollama (service_started), rag-service (started), risk-engine (started), scenario-engine (started) | — | twin_network |
| **fastapi-gateway** | . | `Dockerfile.gateway` | `${GATEWAY_PORT:-8000}:8000` | twin-state-mgr (healthy), forecast-engine (started), scenario-engine (healthy), risk-engine (healthy), rag-service (healthy), copilot-agent (healthy) | — | twin_network |
| **streamlit-dashboard** | . | `Dockerfile.dashboard` | `${DASHBOARD_PORT:-8501}:8501` | fastapi-gateway (service_healthy) | — | twin_network |
| **prometheus** | `prom/prometheus:latest` | — | `9090:9090` | — | `./deployment/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml` | twin_network |
| **grafana** | `grafana/grafana:latest` | — | `3000:3000` | prometheus | `./deployment/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources`, `dashboard.yml:/etc/grafana/provisioning/dashboards`, `dashboards:/var/lib/grafana/dashboards` | twin_network |

### Health Checks

| Service | Test Command | Interval | Timeout | Retries | Start Period |
|---|---|---|---|---|---|
| twin-state-mgr | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"` | 10s | 5s | 3 | — |
| forecast-engine | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')"` | 10s | 5s | 3 | — |
| scenario-engine | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')"` | 10s | 5s | 3 | — |
| risk-engine | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"` | 10s | 5s | 3 | — |
| rag-service | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')"` | 10s | 5s | 3 | — |
| ollama | `ollama list` | 30s | 10s | 5 | 60s |
| copilot-agent | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')"` | 10s | 5s | 3 | — |
| fastapi-gateway | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` | 10s | 5s | 3 | — |
| streamlit-dashboard | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')"` | 10s | 5s | 3 | — |

### Volumes

| Volume | Mount Path | Purpose |
|---|---|---|
| `twin_data` | `/app/data` | State persistence for Digital Twin (Parquet, DuckDB) |
| `model_data` | `/app/models` | Model checkpoints, exports, evaluation artifacts |
| `vector_store` | `/app/knowledge/vector_store` | FAISS index and metadata persistence |
| `ollama_data` | `/root/.ollama` | LLM model storage (Qwen3:8b) |

### Networks

| Network | Driver | Services |
|---|---|---|
| `twin_network` | bridge | All 11 services |
| (default) | bridge | Only used if network not specified |

## 3. Docker Compose Port Matrix (Default Values)

| Port | Service | Config Variable | Default |
|---|---|---|---|
| 8000 | API Gateway | `GATEWAY_PORT` | 8000 |
| 8001 | Twin State Manager | `TWIN_STATE_MGR_PORT` | 8001 |
| 8002 | Scenario Engine | `SCENARIO_PORT` | 8002 |
| 8003 | Risk Engine | `RISK_PORT` | 8003 |
| 8004 | RAG Service | `RAG_PORT` | 8004 |
| 8005 | Copilot Agent | `COPILOT_PORT` | 8005 |
| 8006 | Forecast Engine | `FORECAST_PORT` | 8006 |
| 8501 | Streamlit Dashboard | `DASHBOARD_PORT` | 8501 |
| 11434 | Ollama | — | 11434 |
| 9090 | Prometheus | — | 9090 |
| 3000 | Grafana | — | 3000 |

## 4. Monitoring Services

### Prometheus (profile: monitoring)
- Image: `prom/prometheus:latest`
- Port: 9090
- Scrape interval: 15s
- 7 scrape targets: twin-state-mgr (8001), scenario-engine (8002), risk-engine (8003), rag-service (8004), copilot-agent (8005), forecast-engine (8006), fastapi-gateway (8000)

### Grafana (profile: monitoring)
- Image: `grafana/grafana:latest`
- Port: 3000
- Data source: Prometheus (auto-provisioned at `http://prometheus:9090`)
- Dashboard: Service Health (6-panel stat display for all 6 API services)

### Docker Compose Overlay (`deployment/compose/monitoring.yml`)
- Separate standalone compose file for monitoring stack
- Requires pre-existing `twin_network` (declared as `external: true`)

## 5. Docker Configuration

### `.dockerignore`
30 entries excluding: `.git`, `.github`, `__pycache__`, `*.py[cod]`, `.venv`, `venv`, `node_modules`, `data/`, `logs/`, `output/`, `*.md`, `tests/`, `docs/`, `Makefile`, `pyproject.toml`, `ruff.toml`, `pytest.ini`, `AGENT.md`, `scripts/`

### Nginx Reverse Proxy (`deployment/configs/nginx.conf`)
- Routes `/api/` → `fastapi-gateway:8000`
- Routes `/` → `streamlit-dashboard:8501`
- Includes WebSocket upgrade headers for Streamlit

## 6. Deployment Scripts

| Script | Purpose |
|---|---|
| `deployment/scripts/startup.sh` | Build + start all services, wait 10s, run health check |
| `deployment/scripts/shutdown.sh` | `docker compose down` |
| `deployment/scripts/health_check.sh` | Shell-based health check for all 8 services |
| `deployment/scripts/demo.sh` | 6-step demo walkthrough with URLs |
| `deployment/health/health_check.py` | Python health check utility (5s timeout) |
| `deployment/cd/deploy.sh` | Docker login + `docker compose push` |

## 7. CI/CD Pipeline

### CI (`.github/workflows/ci.yml`)
- Triggers: push/PR to main/master
- Jobs: lint (ruff), test (matrix 3.10/3.12), docker (build 6 images with Buildx)

### CD (`.github/workflows/deploy.yml`)
- Triggers: push of `v*` tags
- Steps: Docker Hub login → `docker compose build` → `docker compose push`
