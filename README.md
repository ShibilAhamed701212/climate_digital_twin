# AI-Powered Digital Twin of India's Climate

**ISRO BAH 2026 — Challenge 5 — Hackathon Proof-of-Concept**

A proof-of-concept AI-powered Digital Twin of India's climate system. Predicts rainfall and temperature, simulates future climate scenarios, and visualizes via an interactive dashboard. Built for the ISRO BAH 2026 hackathon.

**Important:** This is a hackathon prototype. Many features are implemented with synthetic (generated) data and mock services. See [What's Real vs Synthetic](#whats-real-vs-synthetic) below.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)

### Local Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run linter
make lint

# Launch dashboard (synthetic data fallback)
make dashboard
```

### Docker Deployment

```bash
# Build and start all services
make up

# Stop all services
make down

# Full demo walkthrough
make demo
```

### One-Click Demo

```bash
bash deployment/scripts/demo.sh
```

Then open **http://localhost:8501** in your browser.

## What's Real vs Synthetic

| Component | Status |
|-----------|--------|
| **Dashboard app** (Streamlit, 10 pages) | Real — functional, renders with fallback |
| **Backend microservices** (10 Docker services) | Real — all build and start |
| **API client** (dashboard to backend) | Real — with automatic synthetic fallback |
| **ML model architectures** (MLP, LSTM, Transformer) | Real — implemented in code |
| **ML model weights** | Trained on synthetic data only — not production quality |
| **Data files** (`.parquet`, `.csv`) | **Synthetic only** — generated with `np.random.seed(42)` |
| **Data pipeline** (NASA POWER API fetch) | Real code but **never ran on real data** — defaults to synthetic |
| **Dashboard Pages 01–07** | Real UI, backed by synthetic data |
| **Dashboard Pages 08–10** (Knowledge Base, Feedback, BHAI State) | **100% mock data** — no API calls |
| **RAG/Knowledge Base** (FAISS + sentence-transformers) | Real pipeline code, but **index is empty by default** — must re-run indexing |
| **Copilot Agent** | Functional stub — generates mock responses, no real LLM integration |
| **Dashboard navigation** (custom sidebar) | Real — `render_sidebar_nav()` in `sidebar_nav.py` |
| **Sample locations** | Real — 10 Karnataka district coordinates in config |
| **Tests** | Real — 157 test files, all passing |
| **Docker Compose** | Real — 13 services defined, main 10 active |

## Architecture

```
                          ┌─────────────────────────────┐
                          │   Streamlit Dashboard       │
                          │   10 Pages (page_views/)    │
                          │   Port 8501 (8051 in Docker)│
                          └───────────┬─────────────────┘
                                      │
                          ┌───────────▼─────────────────┐
                          │     FastAPI Gateway          │
                          │     Port 8000                │
                          └───┬───┬───┬───┬───┬───┬─────┘
                              │   │   │   │   │   │
      ┌─────────┐  ┌────────┐│ ┌──┴┐ ┌──┴┐ ┌──┴┐ ┌──────────┐
      │Twin State│  │Forecast││ │Scen│ │Risk│ │RAG│ │ Copilot  │
      │ Manager  │  │Engine  ││ │Eng │ │Eng │ │Svc│ │ Agent    │
      │ 8001     │  │ 8006   ││ │8002│ │8003│ │8004│ │ 8005     │
      └─────────┘  └────────┘│ └───┘ └───┘ └───┘ └──────────┘
                             │
                     ┌───────▼────────┐
                     │ Report Service  │
                     │    8007         │
                     └────────────────┘

  Supporting (not in main flow):
    Ollama (11434) → LLM backend for Copilot
    Redis (6379)   → Optional caching
    Prometheus (9090) & Grafana (3000) → Monitoring (profile only)
```

All backend services return synthetic data when real data sources are unavailable. The dashboard falls back to locally-generated synthetic data if any backend service is unreachable.

## Project Structure

```
climate-digital-twin/
├── config/                 # Centralized YAML configuration files
├── data/                   # Synthetic datasets only (parquet, csv)
│   ├── raw/                # Generated with np.random.seed(42)
│   ├── processed/          # Pipeline output (synthetic)
│   └── interim/            # Intermediate pipeline artifacts
├── dashboard/              # Streamlit dashboard (10 pages)
│   ├── page_views/         # 10 page modules (01_ through 10_)
│   ├── services/           # API client with synthetic fallback
│   ├── components/         # Reusable UI components
│   ├── charts/             # Plotly chart builders
│   ├── maps/               # Folium map builders
│   ├── config/             # Dashboard-specific config
│   ├── themes/             # Streamlit theme overrides
│   ├── assets/             # Static assets
│   └── sidebar_nav.py      # Custom sidebar navigation
├── backend/                # FastAPI backend service code
├── models/                 # ML forecasting models (MLP, LSTM, Transformer)
│   ├── models/             # Model architecture definitions
│   ├── predictors/         # Prediction logic
│   └── configs/            # Model hyperparameters
├── simulator/              # Digital Twin engine & scenario simulator
├── risk/                   # Climate risk assessment & SHAP explainability
├── knowledge/              # RAG knowledge base (FAISS + sentence-transformers)
│   ├── data/               # 5 real markdown documents (climate reports/policies)
│   ├── rag.py              # RAG pipeline (FAISS index empty by default)
│   └── configs/            # Chunking & embedding settings
├── copilot/                # Climate Copilot agent (mock responses)
├── pipeline/               # Data processing pipeline (defaults to synthetic)
├── tests/                  # Test suite (~157 test files)
│   ├── unit/               # Unit tests (dashboard, models, simulator, risk, etc.)
│   └── integration/        # Integration tests
├── deployment/             # Docker, CI/CD, monitoring, scripts
│   ├── docker/             # Per-service Dockerfiles
│   ├── scripts/            # Startup, shutdown, demo, health check
│   ├── monitoring/         # Prometheus + Grafana config
│   └── health/             # Python health check utilities
├── runtime/                # BHAI Runtime framework code
├── docs/                   # Documentation
└── docker-compose.yml      # 13 services (10 active, 3 profile-only)
```

## Features

### Implementation Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Scope & Bootstrap | Complete |
| 2 | Data Pipeline | Code complete — runs with synthetic data only |
| 3 | AI Forecasting (MLP/LSTM/Transformer) | Implemented — trained on synthetic data only |
| 4 | Digital Twin Core Engine | Implemented — operates on synthetic state |
| 5 | Geospatial Dashboard | 10 pages, all rendering with synthetic fallback |
| 6 | Scenario Simulation Engine | Implemented — outputs synthetic scenarios |
| 7 | Climate Risk & Explainable AI (SHAP) | Implemented with synthetic data |
| 8 | RAG Knowledge Base (FAISS) | Pipeline code complete — index must be rebuilt to use |
| 9 | Climate Copilot | Functional stub — mock responses, no real LLM |
| 10 | Deployment & DevOps | Docker compose operational |

### Dashboard Pages

| Page | File | Data Source |
|------|------|-------------|
| Climate Overview | `page_views/01_climate_overview.py` | API with synthetic fallback |
| Forecast Viewer | `page_views/02_forecast_viewer.py` | API with synthetic fallback |
| Digital Twin State | `page_views/03_twin_state.py` | API with synthetic fallback |
| Scenario Simulator | `page_views/04_scenario_simulator.py` | API with synthetic fallback |
| Climate Risk | `page_views/05_climate_risk.py` | API with synthetic fallback |
| Reports & Insights | `page_views/06_reports.py` | API with synthetic fallback |
| AI Copilot | `page_views/07_copilot_chat.py` | API with synthetic fallback |
| Knowledge Base | `page_views/08_knowledge_base.py` | **100% mock data** |
| Feedback | `page_views/09_feedback.py` | **100% mock data** |
| Twin State (BHAI) | `page_views/10_twin_state_bhai.py` | **100% mock data** |

### Key Capabilities

- **Rainfall & Temperature Prediction:** 1, 3, and 7-day forecasts using MLP, LSTM, and Transformer architectures (trained on synthetic data)
- **What-If Simulation:** Temperature, rainfall, monsoon, and extreme event scenario analysis (synthetic)
- **Climate Risk Assessment:** Heat, flood, drought, and composite risk scoring with SHAP explanations (synthetic)
- **Semantic Search:** FAISS-based retrieval pipeline — index is empty by default, must be rebuilt
- **AI Climate Copilot:** Multi-agent orchestration structure — returns mock responses
- **Interactive Dashboard:** 10-page Streamlit app with Plotly charts and Folium maps
- **Synthetic Data Fallback:** All pages render with generated data when backends are unreachable

## Docker Services

| Service | Port | Status |
|---------|------|--------|
| fastapi-gateway | 8000 | Active — API gateway |
| twin-state-mgr | 8001 | Active — twin state management |
| scenario-engine | 8002 | Active — scenario simulation |
| risk-engine | 8003 | Active — risk scoring |
| rag-service | 8004 | Active — FAISS-based retrieval |
| copilot-agent | 8005 | Active — mock responses |
| forecast-engine | 8006 | Active — ML forecasting |
| report-service | 8007 | Active — report generation |
| streamlit-dashboard | 8051 (→8501) | Active — frontend |
| ollama | 11434 | Active — LLM backend (no model downloaded by default) |
| redis | 6379 | Optional profile — caching |
| prometheus | 9090 | Monitoring profile — metrics |
| grafana | 3000 | Monitoring profile — dashboards |

## Configuration

All configuration is externalized to YAML files:

- `config/data_config.yaml` — Pipeline settings
- `models/configs/model_config.yaml` — Model hyperparameters
- `simulator/configs/twin_config.yaml` — Twin engine settings
- `simulator/configs/scenario.yaml` — Scenario validation bounds
- `risk/configs/risk.yaml` — Risk scoring weights & thresholds
- `knowledge/configs/rag.yaml` — RAG chunking & embedding settings
- `copilot/configs/copilot.yaml` — LLM, memory & tool registry
- `dashboard/config/config.py` — Dashboard-specific settings

## Make Commands

| Command | Description |
|---------|-------------|
| `make install` | Install Python dependencies (dev) |
| `make install-all` | Install with all extras (dev + ollama) |
| `make test` | Run all tests |
| `make lint` | Run linter (ruff) |
| `make pipeline` | Run data pipeline |
| `make train` | Train forecasting models |
| `make dashboard` | Launch dashboard locally |
| `make docker` | Build Docker images |
| `make up` | Start all services with Docker Compose |
| `make down` | Stop all services |
| `make demo` | Full demo walkthrough |
| `make clean` | Clean temporary files |

## License

For ISRO BAH 2026 hackathon use.
