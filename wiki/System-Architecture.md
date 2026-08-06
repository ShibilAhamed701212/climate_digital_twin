# System Architecture

## Overview

Climate Digital Twin follows a **microservices architecture** where each domain capability runs as an independent service. Services communicate over HTTP within a Docker bridge network and are fronted by a unified FastAPI gateway.

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                                   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │              Streamlit Dashboard (:8501)                        │   │
│   │  Overview │ Forecast │ Twin │ Scenario │ Risk │ Reports │ ...  │   │
│   └──────────────────────────┬──────────────────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────┼──────────────────────────────────────────┐
│                     API LAYER                                            │
│                                                                         │
│   ┌──────────────────────────▼──────────────────────────────────────┐   │
│   │              FastAPI Gateway (:8000)                             │   │
│   │  CORS │ Rate Limiting │ Auth │ Request Logging │ Error Handler  │   │
│   └──┬─────────┬─────────┬─────────┬─────────┬─────────┬───────────┘   │
└──────┼─────────┼─────────┼─────────┼─────────┼─────────┼───────────────┘
       │         │         │         │         │         │
┌──────┼─────────┼─────────┼─────────┼─────────┼─────────┼───────────────┐
│      │    SERVICE LAYER  │         │         │         │                │
│      ▼         ▼         ▼         ▼         ▼         ▼                │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────────┐       │
│  │ Twin │ │Forecast│ │Scenario│ │ Risk │ │ RAG  │ │ Copilot  │       │
│  │ State│ │ Engine │ │ Engine │ │Engine│ │  Svc │ │  Agent   │       │
│  │:8001 │ │ :8006  │ │ :8002  │ │:8003 │ │:8004 │ │  :8005   │       │
│  └──┬───┘ └───┬────┘ └───┬────┘ └──┬───┘ └──┬───┘ └────┬─────┘       │
│     │         │          │         │        │          │               │
│     ▼         ▼          ▼         ▼        ▼          ▼               │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                     DATA LAYER                               │      │
│  │  Parquet Store │ FAISS Index │ Model Registry │ Ollama LLM   │      │
│  └──────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────────┘
```

## Service Descriptions

### Twin State Manager (`:8001`)
Manages the versioned digital twin state. Each location has a current state (temperature, rainfall, humidity) that is updated as new observations arrive. Supports state versioning, rollback, and history queries.

**Key modules:** `simulator/state_manager/`, `simulator/services/twin_service.py`, `simulator/repository/versioned_state_store.py`

### Forecast Engine (`:8006`)
Runs inference using trained forecasting models. Supports multiple architectures (LSTM, Transformer, iTransformer, PatchTST, TimeMixer, XGBoost, Prophet) with ensemble aggregation and physics consistency checks.

**Key modules:** `models/`, `backend/services/forecast/inference.py`

### Scenario Engine (`:8002`)
Executes what-if climate scenarios using Monte Carlo simulation, perturbation models, and ensemble analysis. Supports temperature offsets, rainfall multipliers, and extreme event injection.

**Key modules:** `simulator/engine/monte_carlo.py`, `simulator/engine/perturbation.py`, `simulator/scenarios/`

### Risk Engine (`:8003`)
Computes multi-hazard climate risk scores (heat, flood, drought) with SHAP-based explainability. Includes alert policies, quality gates, deterministic attribution, and historical context analysis.

**Key modules:** `risk/scoring/`, `risk/explainability/`, `risk/evaluation/`

### RAG Service (`:8004`)
Manages the knowledge base with document indexing, chunking, embedding, and retrieval. Uses FAISS for semantic search and BM25 for keyword matching with a hybrid fusion strategy.

**Key modules:** `knowledge/retriever/`, `knowledge/vector_store/`, `knowledge/pipelines/`

### Copilot Agent (`:8005`)
AI-powered conversational assistant. Classifies user intent, plans tool invocations, executes queries against backend services, and generates natural-language responses using Ollama (Qwen 3).

**Key modules:** `copilot/agent/`, `copilot/planner/`, `copilot/workflows/`, `copilot/tools/`

### FastAPI Gateway (`:8000`)
Unified API entry point. Routes requests to appropriate backend services, handles CORS, rate limiting, API key authentication, request/response logging, and error handling.

**Key modules:** `backend/api/`

### Streamlit Dashboard (`:8501`)
10-page interactive frontend built with Streamlit. Features real-time charts (Plotly), spatial maps (Folium), scenario comparison, risk visualization, knowledge base exploration, and an AI chat interface.

**Key modules:** `dashboard/page_views/`, `dashboard/services/api_client.py`

## Data Flow

```
External Data Sources              Internal Processing               User-Facing
───────────────────                ────────────────────              ────────────

  Open-Meteo API  ──┐
                    ├──→ Data Pipeline ──→ Twin State Store ──→ Dashboard
  NASA POWER API  ──┤       │                    │
                    │       ▼                    ▼
  IMD Data        ──┘   Validation         Forecast Engine ──→ API Gateway
                        Feature Eng.             │
                            │                    ▼
                            ▼              Scenario Engine
                      Model Training             │
                            │                    ▼
                            ▼              Risk Assessment ──→ Alerts
                      Model Registry             │
                                                 ▼
                                          RAG + Copilot ──→ Chat Interface
```

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Streamlit, Plotly, Folium, Streamlit-Folium |
| **API** | FastAPI, Uvicorn, Pydantic |
| **ML/Forecasting** | PyTorch, scikit-learn, XGBoost, Prophet, statsmodels |
| **RAG** | FAISS, sentence-transformers, NLTK |
| **LLM** | Ollama (Qwen 3:4B) |
| **Data** | Pandas, NumPy, SciPy, PyArrow, Parquet |
| **Spatial** | GeoPandas, Folium |
| **Infrastructure** | Docker Compose, Prometheus, Grafana, Redis |
| **Testing** | pytest, pytest-cov, pytest-asyncio, ruff, mypy, bandit |
