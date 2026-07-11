# Docker Report

> **⚠️ Docker Compose for local demo. No production containerization.**

---

## Docker Images

| Service | Base Image | Size (approx) | Build Context |
|---------|-----------|---------------|---------------|
| Gateway | nginx:alpine | ~25 MB | `docker/nginx/` |
| Forecasting API | python:3.11-slim | ~1.2 GB | `./api/` |
| Twin API | python:3.11-slim | ~1.2 GB | `./digital_twin/` |
| Scenario Engine | python:3.11-slim | ~1.2 GB | `./scenario_engine/` |
| Risk API | python:3.11-slim | ~1.2 GB | `./risk/` |
| RAG API | python:3.11-slim | ~1.2 GB | `./rag/` |
| Copilot API | python:3.11-slim | ~1.2 GB | `./copilot/` |
| Dashboard | python:3.11-slim | ~1.2 GB | `./app/` |

**Total image size:** ~8–10 GB (all services, without Ollama).

---

## Docker Compose Services

```yaml
services:
  gateway:
    image: nginx:alpine
    ports: ["80:80"]
    depends_on: [api, twin, scenario, risk, rag, copilot, dashboard]
    
  api:
    build: ./api
    ports: ["8005:8005"]
    
  twin:
    build: ./digital_twin
    ports: ["8002:8002"]
    
  scenario:
    build: ./scenario_engine
    ports: ["8003:8003"]
    depends_on: [twin]
    
  risk:
    build: ./risk
    ports: ["8004:8004"]
    
  rag:
    build: ./rag
    ports: ["8006:8006"]
    
  copilot:
    build: ./copilot
    ports: ["8007:8007"]
    
  dashboard:
    build: ./app
    ports: ["8501:8501"]
    depends_on: [api, twin, scenario, risk, rag, copilot]
```

---

## Dependency Graph

```
gateway
  ├── api (standalone)
  ├── twin (standalone)
  ├── scenario → twin
  ├── risk (standalone)
  ├── rag (standalone)
  ├── copilot (standalone)
  └── dashboard → api, twin, scenario, risk, rag, copilot
```

---

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `./data:/app/data` | All services | Shared synthetic data |
| `./models/checkpoints:/app/checkpoints` | API service | Model weights |

---

## Known Docker Issues

1. **Large image sizes.** Each service bundles full Python + PyTorch. Could be optimized with multi-stage builds.
2. **No health check dependency.** `depends_on` only waits for container start, not service readiness.
3. **Ollama model pull required.** 8GB download on first run, not automated.
4. **Streamlit hot-reload broken in container.** Code changes require rebuild.
5. **No dockerignore.** Unnecessary files copied into images.
6. **No network isolation.** All services on default bridge network.
