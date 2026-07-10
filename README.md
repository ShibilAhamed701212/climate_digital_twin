# AI-Powered Digital Twin of India's Climate

**ISRO BAH 2026 — Challenge 5**

A proof-of-concept AI-powered Digital Twin of India's climate system using national datasets. Predicts rainfall and temperature, simulates future climate scenarios, visualizes via an interactive dashboard, and supports climate intelligence queries through an AI assistant.

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

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| `docs/architecture.md` | BHAI Runtime three-layer platform architecture |
| `docs/configuration.md` | Runtime configuration reference |
| `docs/deployment.md` | Docker benchmark deployment guide |
| `docs/development.md` | Developer setup, conventions, extensions |
| `docs/security.md` | Security audit summary (B+ grade) |
| `docs/digital_twin_architecture_plan.md` | 20-phase migration plan to production |
| `docs/climate/overview.md` | Climate plugin registration & capabilities |
| `docs/climate/providers.md` | 6 provider adapter interfaces |
| `docs/climate/stages.md` | 5 climate pipeline stages |
| `docs/climate/workflows.md` | Workflow definitions & execution |
| `docs/copilot/clients.md` | Legacy copilot client adapters |
| `docs/copilot/integration.md` | Runtime-Climate-Copilot integration |

Runtime internals documentation: `runtime/docs/`

## Architecture

```
                     ┌──────────────────┐
                     │  Streamlit Dash  │
                     │    Port 8501     │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │   API Gateway    │
                     │    Port 8000     │
                     └──┬──┬──┬──┬──┬──┘
                        │  │  │  │  │
   ┌─────┐ ┌────┐ ┌────┐│ ┌──┴┐ ┌──┴┐ ┌──────────┐
   │Twin │ │Fore│ │Scen││ │Rsk│ │RAG│ │ Copilot  │
   │Core │ │cast│ │Eng ││ │Eng│ │Svc│ │ Agent    │
   │8001 │ │    │ │8002││ │800│ │800│ │ 8005     │
   └─────┘ └────┘ └────┘│ └───┘ └───┘ └──────────┘
                        │
                  ┌─────▼──────┐
                  │ Forecasting │
                  │   Engine    │
                  └────────────┘
```

## Project Structure

```
climate-digital-twin/
├── docs/                  # BHAI Runtime docs (architecture, config, deployment, security, climate plugin, copilot)
├── data/                  # Raw, interim, processed datasets
├── backend/               # FastAPI backend services
├── models/                # ML forecasting models (MLP, LSTM, Transformer)
├── dashboard/             # Streamlit dashboard (6 pages)
├── simulator/             # Digital Twin engine & scenario simulator
├── risk/                  # Climate risk assessment & SHAP explainability
├── knowledge/             # RAG knowledge base (FAISS + sentence-transformers)
├── copilot/               # Climate Copilot agent (multi-agent orchestration)
├── pipeline/              # Data processing pipeline
├── config/                # Centralized configuration
├── deployment/            # Docker, CI/CD, monitoring, orchestration
│   ├── docker/            # 10 service Dockerfiles
│   ├── compose/           # Docker Compose overlays
│   ├── scripts/           # Startup, shutdown, demo, health check scripts
│   ├── monitoring/        # Prometheus + Grafana config
│   ├── health/            # Python health check utilities
│   ├── configs/           # Nginx, environment templates
│   └── docs/              # Architecture documentation
└── logs/                  # Execution logs
```

## Features

### Phase 1-9 Implemented

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Scope & Bootstrap | ✅ Complete |
| 2 | Data Pipeline | ✅ Complete |
| 3 | AI Forecasting (MLP/LSTM/Transformer) | ✅ Complete |
| 4 | Digital Twin Core Engine | ✅ Complete |
| 5 | Geospatial Dashboard | ✅ Complete |
| 6 | Scenario Simulation Engine | ✅ Complete |
| 7 | Climate Risk & Explainable AI (SHAP) | ✅ Complete |
| 8 | RAG Knowledge Base (FAISS) | ✅ Complete |
| 9 | Climate Copilot (Multi-Agent Orchestration) | ✅ Complete |
| 10 | Deployment & DevOps | ✅ Complete |

### Key Capabilities

- **Rainfall & Temperature Prediction:** 1, 3, and 7-day forecasts using MLP, LSTM, and Transformer architectures
- **What-If Simulation:** Temperature, rainfall, monsoon, and extreme event scenario analysis
- **Climate Risk Assessment:** Heat, flood, drought, and composite risk scoring with SHAP explanations
- **Semantic Search:** FAISS-based retrieval from government reports, ISRO documentation, and research papers
- **AI Climate Copilot:** Multi-agent system (Intent→Planner→Executor→Generator) with conversation memory
- **Interactive Dashboard:** 10-page Streamlit app with Plotly charts, Folium maps, and real-time updates
- **Offline Demo:** Full synthetic data fallback for hackathon environments

## Configuration

All configuration is externalized to YAML files:

- `config/data_config.yaml` — Pipeline settings
- `models/configs/model_config.yaml` — Model hyperparameters
- `simulator/configs/twin_config.yaml` — Twin engine settings
- `simulator/configs/scenario.yaml` — Scenario validation bounds
- `risk/configs/risk.yaml` — Risk scoring weights & thresholds
- `knowledge/configs/rag.yaml` — RAG chunking & embedding settings
- `copilot/configs/copilot.yaml` — LLM, memory & tool registry

## API Endpoints

| Service | Health Endpoint |
|---------|----------------|
| API Gateway | `GET /health` |
| Twin State Manager | `GET /health` |
| Scenario Engine | `GET /health` |
| Risk Engine | `GET /health` |
| RAG Service | `GET /health` |
| Copilot Agent | `GET /health` |

## License

For ISRO BAH 2026 hackathon use.
