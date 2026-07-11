# Quick Start Guide

> **For the synthetic-data demo only. No real data setup required.**

---

## Prerequisites

- **Docker Desktop** (Windows/Mac) or Docker Engine 24+ (Linux)
- **8GB+ RAM** (16GB recommended)
- **10GB free disk space**
- **Git**

---

## 5-Minute Demo Setup

```bash
# 1. Clone and enter
git clone <repo-url>
cd climate-digital-twin

# 2. Start all services
docker compose -f docker/docker-compose.yml up --build -d

# 3. Verify services are healthy
docker compose ps
# All 8 services should show "Up"

# 4. Generate synthetic data
docker exec climate-api python -m scripts.seed_data

# 5. (Optional) Train models on synthetic data
docker exec climate-api python -m scripts.train_models

# 6. Open dashboard
open http://localhost:8501
```

---

## What You'll See

- **Dashboard** at http://localhost:8501 with 10 pages
  - 7 live pages with synthetic data charts
  - 3 mock pages (placeholders)
- **API endpoints** at http://localhost:80 (gateway)
  - `/predict` — synthetic forecasts
  - `/risk/heat` — synthetic risk scores
  - `/scenario/run` — scenario simulation
  - `/copilot/ask` — mock copilot
- **Real-time maps** with synthetic risk overlays

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Port conflict (8501, 8005, etc.) | Another service on same port | Stop conflicting service or change port in docker-compose.yml |
| Service not starting | Missing dependency | `docker compose logs <service>` |
| Dashboard shows no data | Data not generated | Run `docker exec climate-api python -m scripts.seed_data` |
| FAISS index empty | Not populated | Use RAG API `/index` endpoint |
| Copilot returns generic responses | Mock mode | This is expected — no LLM wired |

---

## Shutdown

```bash
docker compose -f docker/docker-compose.yml down
```
