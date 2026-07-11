# System Architecture

The Climate Digital Twin is a **microservice-based hackathon proof-of-concept** for ISRO BAH 2026 Challenge 5. It integrates a domain-agnostic AI Runtime (`runtime/`), domain-specific climate logic, ML forecasting models, RAG knowledge retrieval, and a Streamlit dashboard.

## Layer Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                    │
│          10 pages (page_views/) · Custom sidebar         │
│          Synthetic data fallback when services down      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│               API Gateway (FastAPI) :8000                │
│               Routes to 7+ backend services             │
└──┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┘
   │    │    │    │    │    │    │    │    │    │    │
   ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
┌─────────────────────────────────────────────────────────┐
│              Backend Microservices                       │
│  twin-state-mgr :8001  ·  scenario-engine :8002         │
│  risk-engine :8003       ·  rag-service :8004           │
│  copilot-agent :8005     ·  forecast-engine :8006       │
│  report-service :8007                                    │
├─────────────────────────────────────────────────────────┤
│              Infrastructure                              │
│  nginx (reverse proxy)  ·  Prometheus  ·  Grafana       │
└─────────────────────────────────────────────────────────┘
```

## AI Runtime Core (`runtime/`)

The Runtime is a domain-agnostic orchestration engine (90 Python files). It provides:

- **AgentRuntime** (`runtime/runtime.py`): orchestrator that initializes subsystems, loads plugins, and dispatches pipelines
- **PipelineEngine** (`runtime/pipeline/`): loads pipeline definitions, executes stages with lifecycle hooks
- **Blackboard** (`runtime/blackboard.py`): thread-safe, versioned key-value store for inter-stage communication
- **EventBus** (`runtime/event_bus.py`): pub/sub event system with trace IDs
- **Caching** (`runtime/cache/`): 4 TTL-based caches (provider, retrieval, reasoning, resolution)
- **Reliability** (`runtime/reliability.py`): circuit breaker, retry with exponential backoff
- **Providers** (`runtime/providers/`): provider interface, registry, executor
- **Plugins** (`runtime/plugins/`): plugin interface for domain-specific extensions
- **Workflow** (`runtime/workflow/`): workflow engine + definitions
- **Agents** (`runtime/agents/`): agent interface

The Runtime contains **zero climate-specific concepts** — domain isolation is enforced by architecture tests in `runtime/test_architecture.py`.

## Climate Domain (`climatedt/`)

The `climatedt/` package contains all climate-specific logic (31 files):

- **ML models** (`ml/`): model training and prediction pipelines
- **Pipeline stages** (`pipeline/`): climate-specific pipeline stages (intent, planning, execution, response, verification)
- **RAG** (`rag/`): retrieval-augmented generation for knowledge search
- **Risk** (`risk/`): climate risk assessment logic
- **Scenario** (`scenario/`): what-if scenario simulation
- **Twin** (`twin/`): digital twin state management
- **Storage** (`storage/`): data persistence layer

## Machine Learning Models (`models/`)

Three forecasting architectures implemented (29 files), all **trained on synthetic data**:

| Model | Architecture | Status |
|-------|-------------|--------|
| MLP | Multi-layer Perceptron | Implemented, synthetic training |
| LSTM | Long Short-Term Memory | Implemented, synthetic training |
| Transformer | Attention-based | Implemented, synthetic training |

Additionally: XGBoost risk model (`models/risk/`), scenario perturbation engine (`models/scenario/`).

## Copilot (`copilot/`)

Multi-agent chat system (39 files) that returns **mock responses** — no real LLM integration:

- **Agent orchestrator** (`agent/`): multi-agent workflow
- **Clients** (`clients/`): service client adapters (all mock data)
- **LLM interface** (`llm/`): LLM integration wrapper (stub)
- **Planner** (`planner/`): query planning logic
- **Tools** (`tools/`): agent tool definitions

## Dashboard (`dashboard/`)

Streamlit dashboard with **10 pages in `page_views/`** (NOT `pages/`):

| Page | File | Backend |
|------|------|---------|
| Climate Overview | `01_climate_overview.py` | API client w/ synthetic fallback |
| Forecast Viewer | `02_forecast_viewer.py` | API client w/ synthetic fallback |
| Twin State | `03_twin_state.py` | API client w/ synthetic fallback |
| Scenario Simulator | `04_scenario_simulator.py` | API client w/ synthetic fallback |
| Climate Risk | `05_climate_risk.py` | API client w/ synthetic fallback |
| Reports | `06_reports.py` | API client w/ synthetic fallback |
| Copilot Chat | `07_copilot_chat.py` | Copilot stub (mock responses) |
| Knowledge Base | `08_knowledge_base.py` | **Mock — no API calls** |
| Feedback | `09_feedback.py` | **Mock — no API calls** |
| BHAI Twin State | `10_twin_state_bhai.py` | **Mock — no API calls** |

Custom sidebar navigation via `render_sidebar_nav()` in `dashboard/sidebar_nav.py`.

## Data & Services

### Pipeline (`pipeline/`)

Data ingestion pipeline orchestration (21 files):
- **Sources** (`sources/`): data source connectors (Open-Meteo, NASA POWER)
- **Functions** (`functions/`): pipeline function definitions

### Knowledge Base (`knowledge/`)

RAG pipeline using FAISS + sentence-transformers (30 files):
- **Embeddings** (`embeddings/`): embedding generation with sentence-transformers
- **Vector store** (`vector_store/`): FAISS index interface
- **Documents** (`documents/`): 5 real markdown climate documents
- **Retriever** (`retriever/`): search/retrieval with `generate_answer()` — a simple mock with no real LLM

**Note:** The FAISS index is **EMPTY by default**. Users must re-run indexing to populate it.

### Risk Engine (`risk/`)

Standalone risk assessment service (21 files) with XGBoost-based risk scoring.

### Backend (`backend/`)

FastAPI microservices with health checks (21 files):
- `api/`: API gateway, routers, middleware
- `core/`: shared core logic
- `services/`: individual service implementations

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8000 | FastAPI gateway |
| twin-state-mgr | 8001 | Digital twin state management |
| scenario-engine | 8002 | Scenario simulation |
| risk-engine | 8003 | Risk assessment |
| copilot-agent | 8005 | Copilot chat agent |
| forecast-engine | 8006 | Forecast ML serving |
| dashboard | 8501/8051 | Streamlit UI |
| nginx | 80 | Reverse proxy |
| prometheus | 9090 | Metrics |
| grafana | 3000 | Visualizations |

## Data Status

| Component | Reality |
|-----------|---------|
| All committed data (.parquet, .csv) | **SYNTHETIC** — generated with `np.random.seed(42)` |
| Pipeline data fetching | Code exists but **defaults to synthetic** |
| NASA POWER API | Implemented but **never ran with real data** |
| 15 sample locations | Hardcoded Karnataka districts in config |
| Model weights | **Trained on synthetic data only** |
| FAISS index | **Empty by default** — user must re-run indexing |
| Copilot/generate_answer() | **Simple mock** — no real LLM |
| Dashboard integration with models | **Not connected** to frontend |

## Key Design Decisions

- **Runtime is domain-agnostic**: verified by AST-level architecture tests
- **Stages communicate through Blackboard only**: no direct stage-to-stage coupling
- **API client has synthetic fallback**: dashboard works even when services are unavailable
- **Evidence is immutable**: once created, Evidence objects are not mutated
- **Caching is layered**: 4 caches with different TTL strategies
- **Pages in `page_views/`** (not `pages/`): custom sidebar navigation replaces Streamlit native
