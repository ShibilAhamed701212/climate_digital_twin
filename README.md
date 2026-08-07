<div align="center">

# 🌍 Climate Digital Twin

**AI-Powered Climate Digital Twin for India**

*Real-time climate monitoring, multi-model forecasting, scenario simulation, and risk assessment — powered by a microservices architecture and an interactive Streamlit dashboard.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![Code Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen.svg)](https://github.com/ShibilAhamed701212/climate_digital_twin)

</div>

---

## 📖 Overview

Climate Digital Twin is a full-stack platform that creates a **digital replica of India's climate system**, focused on the Karnataka region. It ingests real-time weather data from multiple providers (Open-Meteo, NASA POWER, IMD), runs physics-informed simulations, generates multi-horizon forecasts using an ensemble of deep learning models, and provides actionable climate risk assessments — all accessible through a rich interactive dashboard and a RESTful API gateway.

### Key Capabilities

| Capability | Description |
|---|---|
| **🔄 Digital Twin State** | Versioned, observable replica of regional climate state with real-time data synchronization |
| **📈 Multi-Model Forecasting** | Ensemble of 8 model architectures (LSTM, Transformer, XGBoost, Prophet, Baseline, plus simplified implementations inspired by iTransformer, PatchTST, and TimeMixer) |
| **🔮 Scenario Simulation** | Monte Carlo simulation engine with perturbation models for what-if climate scenarios |
| **⚠️ Climate Risk Assessment** | Automated heat, flood, and drought risk scoring with SHAP explainability |
| **📚 Knowledge Base (RAG)** | FAISS vector store with hybrid semantic + BM25 search over climate documents |
| **🤖 AI Copilot** | Conversational AI assistant powered by Ollama (Qwen 3) for natural-language climate queries |
| **🗺️ Spatial Analysis** | Grid-based twin with coupled simulation processes (evapotranspiration, runoff, soil water, SPEI drought) |
| **📊 Interactive Dashboard** | 10-page Streamlit dashboard with real-time charts, maps, and Folium-based spatial views |

---

## 🏗️ Architecture

The platform follows a **microservices architecture** with 10 containerized services communicating over an internal Docker network:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard (:8501)                    │
│  Climate Overview │ Forecasts │ Twin State │ Scenarios │ Risk │ ...  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway (:8000)                            │
│  /twin  /forecast  /scenario  /risk  /rag  /feedback  /health       │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬────────────┘
   │          │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│ Twin │ │Forecast│ │Scenario│ │ Risk │ │ RAG  │ │ Copilot  │
│ State│ │ Engine │ │ Engine │ │Engine│ │Service│ │  Agent   │
│:8001 │ │ :8006  │ │ :8002  │ │:8003 │ │:8004 │ │  :8005   │
└──────┘ └────────┘ └────────┘ └──────┘ └──────┘ └────┬─────┘
                                                       │
                                                  ┌────▼─────┐
                                                  │  Ollama  │
                                                  │ :11434   │
                                                  └──────────┘
```

**Supporting Services:** Report Service (:8007) · Redis (optional) · Prometheus + Grafana (monitoring profile)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for containerized deployment)
- **4 GB+ RAM** (8 GB recommended for full stack with Ollama)

### Option 1 — Local Development

```bash
# 1. Clone the repository
git clone https://github.com/ShibilAhamed701212/climate_digital_twin.git
cd climate_digital_twin

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Copy environment configuration
cp .env.example .env

# 5. Start the API gateway
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Start the dashboard (in a separate terminal)
streamlit run dashboard/app.py
```

### Option 2 — Docker Compose (Full Stack)

```bash
# Build and start all services
make up

# Or manually:
docker compose up --build -d

# Access the services:
#   Dashboard:        http://localhost:8501
#   API Gateway:      http://localhost:8000
#   API Docs:         http://localhost:8000/docs
```

### Option 3 — Local Services Script (Windows)

```powershell
# Start all backend microservices locally
.\scripts\start_local_services.ps1
```

---

## 📁 Project Structure

```
climate-digital-twin/
│
├── backend/                  # FastAPI API gateway & route handlers
│   ├── api/                  #   Routes: twin, forecast, scenario, risk, rag, feedback
│   ├── core/                 #   Shared backend utilities
│   └── services/             #   Forecast inference service
│
├── climatedt/                # Core domain library (facade package)
│   ├── simulation/           #   Coupled simulation engine (Penman-Monteith ET, SCS runoff, SPEI)
│   ├── spatial/              #   Grid-based twin & spatial operations
│   ├── ml/                   #   Machine learning utilities
│   ├── twin/                 #   Twin state management
│   ├── risk/                 #   Risk service facade
│   ├── rag/                  #   RAG service facade
│   └── ...                   #   forecast, scenario, feedback, data, integrity, storage
│
├── simulator/                # Digital twin simulation engine
│   ├── engine/               #   Monte Carlo, perturbation, scenario, twin engines
│   ├── scenarios/            #   Scenario generation, comparison, ensemble analysis
│   ├── entities/             #   Climate entity models
│   ├── graph/                #   Entity graph for spatial relationships
│   ├── synchronizer/         #   Real-time data synchronization with twin state
│   ├── reconciliation/       #   Observation-simulation reconciliation
│   └── ...                   #   anomaly, conflict, events, historical, validators
│
├── models/                   # ML forecasting models
│   ├── lstm/                 #   LSTM recurrent model
│   ├── transformer/          #   Vanilla Transformer model
│   ├── itransformer/         #   Inverted Transformer (iTransformer)
│   ├── patchtst/             #   Patch Time Series Transformer
│   ├── timemixer/            #   TimeMixer architecture
│   ├── xgboost/              #   XGBoost gradient boosting
│   ├── prophet/              #   Facebook Prophet
│   ├── baseline/             #   Statistical baseline model
│   ├── ensemble/             #   Ensemble aggregation
│   ├── registry/             #   Model registry & versioning
│   └── tuning/               #   Hyperparameter tuning
│
├── risk/                     # Climate risk assessment engine
│   ├── scoring/              #   Heat, flood, drought, and composite risk scoring
│   ├── explainability/       #   SHAP-based feature attribution & insight generation
│   ├── evaluation/           #   Hazard evaluator, alert policies, quality gates
│   ├── models/               #   Risk data models (hazard assessments)
│   └── store/                #   Alert & hazard persistent stores
│
├── knowledge/                # RAG knowledge base
│   ├── retriever/            #   Hybrid search (semantic + BM25), context builder
│   ├── embeddings/           #   Sentence-transformer embeddings
│   ├── vector_store/         #   FAISS index management
│   ├── chunkers/             #   Document chunking strategies
│   ├── loaders/              #   Document loaders (Markdown, CSV, JSON)
│   ├── pipelines/            #   Indexing pipeline
│   └── documents/            #   Climate knowledge documents (IMD, ISRO, govt, research)
│
├── copilot/                  # AI Copilot assistant service
│   ├── agent/                #   Intent classification agent
│   ├── planner/              #   Query planning & tool selection
│   ├── workflows/            #   Orchestrator, executor, response generator
│   ├── tools/                #   Forecast, risk, RAG, scenario, twin, report tools
│   ├── llm/                  #   Ollama LLM client
│   ├── memory/               #   Conversation memory
│   └── prompts/              #   System & tool prompt templates
│
├── pipeline/                 # Data ingestion & processing pipeline
│   ├── providers/            #   Open-Meteo, NASA POWER, IMD data providers
│   ├── sources/              #   Location registry & data source management
│   ├── stores/               #   Observation & rejected data stores
│   └── functions/            #   Pipeline function utilities
│
├── dashboard/                # Streamlit interactive dashboard
│   ├── page_views/           #   10 page modules (overview, forecast, twin, scenarios, ...)
│   ├── components/           #   Sidebar, navigation, reusable UI components
│   ├── services/             #   API client for backend communication
│   ├── charts/               #   Chart rendering utilities
│   ├── maps/                 #   Folium map components
│   └── assets/               #   CSS styling & static assets
│
├── config/                   # Runtime configuration files
├── data/                     # Data storage (raw, processed, twin store, scenarios)
├── deployment/               # Docker, CI/CD, monitoring, and health checks
│   ├── docker/               #   10 Dockerfiles for each microservice
│   ├── monitoring/           #   Prometheus & Grafana configuration
│   ├── health/               #   Health check scripts
│   └── scripts/              #   Deployment helper scripts
│
├── scripts/                  # Operational scripts (seeding, indexing, verification)
├── tests/                    # Test suite (unit + integration, 86% coverage)
├── wiki/                     # GitHub Wiki source pages
│
├── docker-compose.yml        # Full-stack Docker Compose (10 services)
├── docker-compose.prod.yml   # Production compose overrides
├── Makefile                  # Developer workflow commands
├── pyproject.toml            # Python project configuration & dependencies
└── LICENSE                   # MIT License
```

---

## 🧠 Forecasting Models

The platform implements **8 forecasting architectures** with automated training, evaluation, and ensemble aggregation:

| Model | Type | Description |
|---|---|---|
| **LSTM** | Deep Learning | Long Short-Term Memory for sequential climate patterns |
| **Transformer** | Deep Learning | Self-attention based temporal modeling |
| **iTransformer** | Deep Learning | Inverted Transformer — treats variables as tokens |
| **PatchTST** | Deep Learning | Patch-based Time Series Transformer |
| **TimeMixer** | Deep Learning | Multi-scale temporal mixing architecture |
| **XGBoost** | Gradient Boosting | Tabular gradient boosting with feature engineering |
| **Prophet** | Statistical | Facebook Prophet for trend + seasonality decomposition |
| **Baseline** | Statistical | Persistence and climatology baselines |

**Ensemble:** Weighted model aggregation with physics-informed consistency checks.

---

## ⚠️ Risk Assessment

The risk engine provides multi-hazard climate risk scoring:

- **🌡️ Heat Risk** — Consecutive hot days, seasonal anomaly detection, threshold exceedance
- **🌧️ Flood Risk** — Rainfall intensity, multi-day accumulation, forecast uncertainty
- **☀️ Drought Risk** — Rainfall deficit, dry period duration, temperature stress
- **📊 Composite Risk** — Weighted aggregation across all hazard types
- **🔍 Explainability** — SHAP-based feature attribution for every risk score

---

## 🔮 Scenario Simulation

The scenario engine supports interactive what-if analysis:

- **Monte Carlo Engine** — Stochastic ensemble simulation with configurable sample sizes
- **Perturbation Models** — Temperature offsets, rainfall multipliers, extreme event injection
- **Scenario Comparison** — Side-by-side comparison of baseline vs. perturbed futures
- **Ensemble Analysis** — Statistical aggregation across Monte Carlo runs

---

## 📚 Knowledge Base (RAG)

The Retrieval-Augmented Generation system provides domain-specific climate knowledge:

- **Document Sources** — IMD weather data, ISRO satellite observations, government reports, risk assessments, research papers
- **Hybrid Search** — Combines FAISS semantic search with BM25 keyword matching
- **Sentence Embeddings** — Powered by `sentence-transformers` for dense retrieval
- **Context Builder** — Assembles relevant context for the AI Copilot

---

## 🛠️ Development

### Running Tests

```bash
# Run the full test suite with coverage
make test

# Or directly:
pytest tests/ -v --cov --cov-report=term-missing
```

### Linting

```bash
make lint

# Or directly:
ruff check .
```

### Useful Make Commands

| Command | Description |
|---|---|
| `make install` | Install Python dependencies (dev) |
| `make test` | Run all tests |
| `make lint` | Run ruff linter |
| `make pipeline` | Run data ingestion pipeline |
| `make train` | Train forecasting models |
| `make dashboard` | Launch dashboard locally |
| `make up` | Start all services via Docker Compose |
| `make down` | Stop all services |
| `make demo` | Full demo walkthrough |
| `make clean` | Clean temporary files |

### Data Seeding

```bash
# Seed twin state with sample data
python scripts/seed_twin_data.py

# Seed forecast data
python scripts/seed_forecast_data.py

# Index knowledge base documents
python scripts/index_knowledge_base.py
```

---

## 🐳 Docker Services

| Service | Port | Description |
|---|---|---|
| `streamlit-dashboard` | 8501 | Interactive Streamlit dashboard |
| `fastapi-gateway` | 8000 | API gateway (all endpoints) |
| `twin-state-mgr` | 8001 | Twin state management service |
| `scenario-engine` | 8002 | Scenario simulation service |
| `risk-engine` | 8003 | Risk assessment service |
| `rag-service` | 8004 | RAG knowledge retrieval service |
| `copilot-agent` | 8005 | AI Copilot chat service |
| `forecast-engine` | 8006 | Forecast inference service |
| `report-service` | 8007 | Report generation service |
| `ollama` | 11434 | Local LLM inference (Qwen 3) |

**Optional:** Redis (caching), Prometheus + Grafana (monitoring profile)

---

## 🌐 API Endpoints

The FastAPI gateway exposes the following endpoint groups:

| Route Group | Endpoints | Description |
|---|---|---|
| `/health` | `GET /health`, `GET /health/ready` | Service health & readiness |
| `/twin` | `GET/POST /twin/state` | Digital twin state operations |
| `/forecast` | `GET /forecast/predict` | Multi-model climate forecasts |
| `/scenario` | `POST /scenario/simulate` | Scenario simulation requests |
| `/risk` | `GET /risk/assess` | Climate risk assessments |
| `/rag` | `POST /rag/query`, `GET /rag/search` | Knowledge base queries |
| `/feedback` | `POST /feedback` | User feedback capture |

Full OpenAPI documentation available at `http://localhost:8000/docs`

---

## 📋 Configuration

| File | Purpose |
|---|---|
| `.env` / `.env.example` | Environment variables (ports, API keys, data dirs) |
| `config/data_config.yaml` | Data sources, provider priority, pipeline settings |
| `config/risk_config.yaml` | Risk scoring thresholds and weights |
| `config/schedules.yaml` | Scheduled pipeline execution |
| `copilot/configs/` | Copilot agent prompts and LLM settings |
| `knowledge/configs/` | RAG indexing and retrieval settings |
| `models/configs/` | Model hyperparameters and training configs |
| `simulator/configs/` | Simulation engine parameters |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

<div align="center">

**Built with ❤️ for climate resilience**

</div>
