# Deployment Guide

The Climate Digital Twin is deployed as a multi-service Docker stack for the ISRO BAH 2026 hackathon. 7 core microservices + 3 infrastructure services.

## Docker Compose Setup

### Main Services (`docker-compose.yml`)

```yaml
services:
  twin-state-mgr:     # Port 8001 — Digital twin state
  forecast-engine:    # Port 8006 — ML forecast serving
  scenario-engine:    # Port 8002 — Scenario simulation
  risk-engine:        # Port 8003 — Risk assessment
  copilot-agent:      # Port 8005 — Copilot chat
  rag-service:        # Port 8004 — RAG knowledge
  report-service:     # Port 8007 — Report generation
  api-gateway:        # Port 8000 — FastAPI gateway
  dashboard:          # Port 8051 — Streamlit UI
  nginx:              # Port 80 — Reverse proxy
  prometheus:         # Port 9090 — Metrics
  grafana:            # Port 3000 — Dashboards
```

### Resource Requirements

| Service | Memory Limit | CPU Limit |
|---------|-------------|-----------|
| twin-state-mgr | 2G | 1.0 |
| forecast-engine | 4G | 2.0 |
| scenario-engine | 2G | 1.0 |
| risk-engine | 2G | 1.0 |
| other services | 512M–1G | 0.5–1.0 |

Total minimum: ~16GB RAM, 8+ CPU cores recommended.

### Storage Volumes

- `twin_data`: Persistent twin state storage
- `model_data`: ML model artifacts and weights

## Quick Start

### Prerequisites
- Docker & Docker Compose v2+
- 16GB+ RAM recommended
- Python 3.11+ (for local development only)

### Build and Run

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# Check service health
docker compose ps

# View logs
docker compose logs -f api-gateway

# Stop all services
docker compose down
```

### Access Services

| Service | URL | Notes |
|---------|-----|-------|
| Dashboard | http://localhost:8501 | Port 8051 in Docker |
| API Gateway | http://localhost:8000 | REST API |
| Nginx | http://localhost:80 | Load balancer |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3000 | Dashboards |

## Production Override (`docker-compose.prod.yml`)

Additional production configuration:
- Resource limits and reservations
- Logging configuration (json-file, 10MB max, 3 files)
- Health checks on all services
- Restart policy: `unless-stopped`

## Local Development

### Install Dependencies

```bash
pip install -e ".[dev]"
```

### Run Dashboard Locally

```bash
cd dashboard
streamlit run app.py
# Dashboard at http://localhost:8501
# Uses synthetic data fallback — no Docker services needed
```

### Run Tests

```bash
pytest tests/ -v
# 2,266 tests
```

## Benchmark Execution

```bash
# Run runtime benchmarks
pytest runtime/benchmarks/ -v

# With benchmark metrics
pytest runtime/benchmarks/ -v --benchmark
```

## Known Issues

- Docker Python version may mismatch `pyproject.toml` requirement (>=3.11) — flagged in security audit
- pip and wheel in Docker image have known CVEs in build toolchain — upgrade with `pip install --upgrade pip wheel`
- Dashboard uses port **8051** inside Docker (mapped to 8501 externally in override)
- All data is **synthetic** — no real climate data feeds
- Copilot agent returns **mock responses** — no real LLM integration
- Default RAG FAISS index is **empty** — must re-run indexing

## Architecture

See `docs/architecture.md` for the full system architecture diagram.
