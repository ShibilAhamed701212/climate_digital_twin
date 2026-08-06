# Deployment Guide

## Overview

The Climate Digital Twin is packaged for cloud-native deployment using Docker Compose, containerized microservices, health probes, and optional Prometheus/Grafana observability profiles.

---

## Deployment Architecture

```
                       ┌─────────────────────────┐
                       │   Reverse Proxy / ALB   │
                       └────────────┬────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────┐                         ┌────────────────────┐
│ Streamlit Dashboard   │                         │ FastAPI Gateway    │
│ Container (:8501)     │                         │ Container (:8000)  │
└───────────────────────┘                         └─────────┬──────────┘
                                                            │
    ┌─────────────────┬─────────────────┬──────────────────┼─────────────────┐
    ▼                 ▼                 ▼                  ▼                 ▼
┌────────┐       ┌────────┐       ┌────────┐          ┌────────┐        ┌────────┐
│ Twin   │       │Forecast│       │Scenario│          │ Risk   │        │ RAG    │
│ State  │       │ Engine │       │ Engine │          │ Engine │        │ Svc    │
│ (:8001)│       │ (:8006)│       │ (:8002)│          │ (:8003)│        │ (:8004)│
└────────┘       └────────┘       └────────┘          └────────┘        └────────┘
```

---

## Environment Configuration (`.env`)

Key production configuration settings:

```ini
# Production Environment Settings
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1

# Microservice Ports
GATEWAY_PORT=8000
TWIN_STATE_MGR_PORT=8001
SCENARIO_PORT=8002
RISK_PORT=8003
RAG_PORT=8004
COPILOT_PORT=8005
FORECAST_PORT=8006
REPORT_PORT=8007
DASHBOARD_PORT=8501

# External APIs
OPEN_METEO_ENABLED=true
NASA_POWER_ENABLED=true
CDS_API_KEY=your-key-here

# LLM Config
OLLAMA_HOST=http://ollama:11434
LLM_MODEL=qwen3:4b
```

---

## Production Deployment Commands

### Standard Deployment (All Core Services)

```bash
# Build and start services in detached mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Verify container health status
docker compose ps
```

### Deployment Profiles

- **Core Microservices**: `docker compose up -d`
- **Optional Redis Cache**: `docker compose --profile optional up -d`
- **Monitoring Stack (Prometheus + Grafana)**: `docker compose --profile monitoring up -d`

---

## Health Checks & Monitoring

Every container includes explicit `HEALTHCHECK` instructions:
- **API Gateway**: `GET http://localhost:8000/health`
- **Dashboard**: `GET http://localhost:8501`
- **Prometheus**: Scraping metrics at `http://localhost:9090`
- **Grafana**: Pre-configured dashboard dashboards at `http://localhost:3000` (User: `admin`, Pass: `admin`)

---

## Backup & Persistence

Persistent Docker volumes preserve runtime state across container restarts:
- `twin_data`: Parquet store for versioned twin states
- `model_data`: Trained model checkpoints
- `vector_store`: FAISS indices for RAG retrieval
- `ollama_data`: Downloaded LLM weights
