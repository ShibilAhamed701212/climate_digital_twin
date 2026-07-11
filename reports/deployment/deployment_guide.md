# Deployment Guide

> **⚠️ Docker deployment for local demo only. No production deployment tested.**

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2+
- 8GB+ RAM (16GB recommended)
- 10GB free disk space
- Ollama (optional, for future LLM integration)

---

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd climate-digital-twin

# 2. Build and start all services
docker compose -f docker/docker-compose.yml up --build -d

# 3. Verify all services are healthy
docker compose ps

# 4. Generate synthetic data
docker exec climate-api python -m scripts.seed_data

# 5. Train models (optional — uses synthetic data)
docker exec climate-api python -m scripts.train_models

# 6. Access dashboard
open http://localhost:8501
```

---

## Service URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8501 |
| API Gateway | http://localhost:80 |
| Forecasting API | http://localhost:8005 |
| Twin API | http://localhost:8002 |
| Scenario Engine | http://localhost:8003 |
| Risk API | http://localhost:8004 |
| RAG API | http://localhost:8006 |
| Copilot API | http://localhost:8007 |
| Ollama | http://localhost:11434 |

---

## Ollama Setup (For Future LLM Integration)

```bash
# Pull the model (8GB download)
docker exec ollama ollama pull qwen3:8b

# Verify
docker exec ollama ollama list
```

**Note:** The copilot service is not currently wired to Ollama. This setup is forward-looking.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | Data storage path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `API_HOST` | `0.0.0.0` | API bind address |
| `ENVIRONMENT` | `development` | Runtime environment |

---

## Not Production-Ready

This deployment is suitable for **local development and hackathon demos only**. For production:

| Gap | Issue |
|-----|-------|
| No authentication | All endpoints are open |
| No HTTPS | HTTP only |
| No secrets management | API keys in environment variables |
| No database | In-memory state, Parquet files |
| No backup/restore | Data persistence not configured |
| No health checks | Basic Docker health only |
| No scaling | Single-instance per service |
| No monitoring | Prometheus/Grafana defined but not configured |
| No CI/CD | Manual docker compose only |
