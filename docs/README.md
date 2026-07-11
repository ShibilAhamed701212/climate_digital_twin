# Climate Digital Twin — ISRO BAH 2026 (Challenge 5)

**Hackathon Proof-of-Concept** — AI-Powered Digital Twin of India's Climate System

**Version 0.1.0** — 2,266 tests passing, 23% coverage (target 80%), 375+ Python files across 10 packages.

A proof-of-concept integrating Streamlit dashboards, ML forecasting models (MLP/LSTM/Transformer), microservice backend, and a domain-agnostic AI Runtime (`runtime/`) into a climate digital twin for Karnataka, India.

**Important:** This is a hackathon prototype. All data files are synthetic (generated with `np.random.seed(42)`). The ML models are trained on synthetic data only. See [What's Real vs Synthetic](#whats-real-vs-synthetic) below.

---

## Architecture Overview

```
                    ┌──────────────────────────────────┐
                    │     Streamlit Dashboard          │
                    │   10 Pages (page_views/)         │
                    │   Port 8501 (8051 in Docker)     │
                    └──────────┬───────────────────────┘
                               │
                    ┌──────────▼───────────────────────┐
                    │     API Gateway (FastAPI)        │
                    │     Port 8000                    │
                    └──┬────┬────┬────┬────┬────┬──────┘
                       │    │    │    │    │    │
     ┌─────────────────┘    │    │    │    │    └──────────────────┐
     ▼                      ▼    ▼    ▼    ▼                       ▼
┌──────────┐  ┌──────────┐ ┌────┐ ┌───┐ ┌────┐ ┌──────────┐  ┌───────┐
│Twin State│  │ Forecast │ │Scen│ │Rsk│ │RAG │ │ Copilot  │  │Report │
│ Manager  │  │ Engine   │ │Eng │ │Eng│ │Svc │ │ Agent    │  │Service │
│ :8001    │  │ :8006    │ │:802│ │:03│ │:804│ │ :8005    │  │ :8007  │
└──────────┘  └──────────┘ └────┘ └───┘ └────┘ └──────────┘  └───────┘
```

7 core microservices, plus nginx (load balancer), Prometheus/Grafana (monitoring), and optionally Ollama (LLM backend).

---

## What's Real vs Synthetic

| Component | Status |
|-----------|--------|
| **Dashboard** (Streamlit, 10 pages, custom sidebar) | **Real** — renders all pages, handles missing data gracefully |
| **Backend microservices** (7 Docker services) | **Real** — all build and start |
| **API Client** (dashboard → backend) | **Real** — with automatic synthetic data fallback when services unavailable |
| **ML architectures** (MLP, LSTM, Transformer) | **Real** — implemented, trained on synthetic data |
| **Model weights** | **Synthetic-only training** — not production quality |
| **All .parquet / .csv data files** | **Synthetic** — generated with `np.random.seed(42)` |
| **NASA POWER API integration** | Code exists but **never ran on real data** — defaults to synthetic |
| **Dashboard Pages 01–07** | Real UI, backed by API client with synthetic fallback |
| **Dashboard Pages 08–10** (Knowledge Base, Feedback, BHAI State) | **100% mock UI** — no API calls |
| **RAG/Knowledge Base** (FAISS + sentence-transformers) | Pipeline code exists, but **FAISS index is EMPTY by default** — re-run indexing to populate |
| **Copilot Agent** | Functional **stub** — returns mock responses, no real LLM integration |
| **Runtime (`runtime/`)** | Real — domain-agnostic orchestration engine (90 Python files) |
| **Sample locations** | Real — 10 Karnataka district coordinates in config |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose

### Local Development
```bash
# Install
pip install -e ".[dev]"

# Run dashboard with synthetic data fallback
cd dashboard && streamlit run app.py

# Run tests
pytest tests/
```

### Docker Deployment
```bash
# Build & start all services
docker compose up --build

# Dashboard at http://localhost:8501
# (port 8051 in Docker override)
```

---

## Project Structure

```
├── backend/           FastAPI microservices (21 files)
│   ├── api/           API gateway (port 8000)
│   ├── core/          Shared core logic
│   └── services/      Individual service apps
├── climatedt/         Climate domain logic (31 files)
│   ├── ml/            ML training/prediction
│   ├── pipeline/      Climate-specific pipeline stages
│   ├── rag/           Retrieval-Augmented Generation
│   ├── risk/          Risk assessment
│   ├── scenario/      Scenario simulation
│   ├── storage/       Data storage layer
│   └── twin/          Digital twin state
├── config/            Data configuration (YAML)
├── copilot/           Copilot agent system (39 files)
│   ├── agent/         Agent orchestration
│   ├── clients/       Service client adapters
│   ├── llm/           LLM integration (stub)
│   └── planner/       Query planning
├── dashboard/         Streamlit dashboard (31 files)
│   ├── app.py         Entry point
│   ├── page_views/    10 dashboard pages
│   ├── services/      API client + synthetic fallback
│   ├── components/    Reusable UI components
│   ├── config/        Dashboard configuration
│   └── sidebar_nav.py Custom sidebar navigation
├── data/              Data files (all synthetic)
├── deployment/        Docker files, scripts
├── docs/              Documentation
├── knowledge/         RAG pipeline (30 files)
│   ├── embeddings/    Embedding generation
│   ├── vector_store/  FAISS interface
│   ├── documents/     Source markdown docs
│   └── retriever/     Search/retrieval
├── models/            ML model definitions (29 files)
│   ├── forecasting/   MLP, LSTM, Transformer
│   ├── risk/          XGBoost risk model
│   └── scenario/      Perturbation engine
├── pipeline/          Pipeline orchestration (21 files)
├── reports/           Generated reports & diagrams
├── risk/              Risk engine (21 files)
├── runtime/           AI Runtime engine (90 files)
│   ├── pipeline/      Pipeline engine + stages
│   ├── models/        Data models
│   ├── cache/         TTL-based caching
│   ├── providers/     Provider interface + registry
│   ├── plugins/       Plugin interface + loader
│   ├── events/        Event definitions
│   ├── agents/        Agent interface
│   ├── workflow/      Workflow engine
│   ├── benchmarks/    Performance benchmarks
│   └── tests/         Architecture + unit tests
├── scripts/           Utility scripts
├── simulator/         Scenario simulator (62 files)
└── tests/             All tests (2,266 tests)
```

---

## Key Features

- **10-page Streamlit dashboard** with custom sidebar navigation
- **7+ Docker microservices** with health checks and resource limits
- **ML forecasting** (MLP, LSTM, Transformer) trained on synthetic data
- **Scenario simulation** (temperature, rainfall, monsoon, extreme event perturbations)
- **Risk assessment** (heat, flood, drought, composite risk scoring)
- **RAG knowledge base** (FAISS + sentence-transformers, index must be re-built)
- **Copilot chat agent** (mock responses — no real LLM)
- **Domain-agnostic AI Runtime** with pipeline/workflow engine, Blackboard, EventBus
- **API client with synthetic data fallback** — dashboard works even when services are down
