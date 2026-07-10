# Release Notes — v1.0.0

**Release Date:** 2026-06-29
**Project:** AI-Powered Digital Twin of India's Climate (ISRO BAH 2026 — Challenge 5)
**Repository:** `climate-digital-twin`

---

## Executive Summary

The Climate Digital Twin v1.0.0 is a proof-of-concept AI-powered Digital Twin of India's climate system, scoped to Karnataka state. The system predicts rainfall and temperature, simulates future climate scenarios, assesses climate risk with explainable AI, and provides natural-language climate intelligence via an LLM-powered Copilot agent — all containerized for one-command deployment with full synthetic data fallback for offline hackathon environments.

### Key Metrics

| Metric | Value | Change |
|---|---|---|
| Product Readiness Score | **72/100** | +30 (from 42/100) |
| Total Tests | **656** | — |
| Passing Tests | **239** (unit) + **18** (known env failures) | — |
| E2E Pipeline Stages | **17/17** passing | 100% |
| Forecasting Models | **7** architectures (3 trained, 3 stubs, 1 ensemble) | — |
| Best RMSE | **4.53** (LSTM) | — |
| R² Score | **0.87** (all trained models) | — |
| Docker Services | **11** (8 app + Ollama + Prometheus + Grafana) | — |
| Dashboard Pages | **7** | — |
| Copilot Tools | **6** | — |
| Risk Categories | **5** (Very Low → Severe) | — |
| Scenario Presets | **11** | — |
| Config YAML Files | **7** | — |
| API Endpoints | **32** | — |

---

## What's New

### Phase 1 — Scope & Bootstrap
- Repository structure with 54 Python packages
- 8 Dockerfiles with HEALTHCHECK instructions
- Docker Compose with 11 services, dependency ordering, volumes, networks
- CI/CD with GitHub Actions (lint on 3.12, test matrix 3.10/3.12, Docker build)
- Pre-commit hooks (ruff, isort, trailing-whitespace, secret detection)

### Phase 2 — Data Pipeline
- Data downloader with NASA POWER API support + synthetic fallback
- Dataset validator (file existence, columns, date range, lat/lon bounds, value ranges)
- Data cleaner (duplicate removal, missing value interpolation, outlier clipping)
- Feature engineering (12 features: DayOfYear, Month, Week, Season, Monsoon, RollingRain7/30, RollingTemp7/30, TempDiff, RainfallTrend, PriorRain7/30)
- Chronological 70/15/15 train/val/test split with CSV export
- End-to-end pipeline orchestrator with quality report generation

### Phase 3 — AI Forecasting Engine
- **7 model architectures:**
  - **Baseline (MLP):** Feed-forward network, 94.5 KB checkpoint, RMSE 4.59
  - **LSTM:** Stacked 2-layer LSTM, 802.3 KB, RMSE 4.53 (best)
  - **Transformer:** 3-layer encoder with positional encoding, 2,847 KB, RMSE 4.57 (fastest trained)
  - **PatchTST:** Patch-based time series transformer (stub, untrained)
  - **TimeMixer:** Multi-scale mixing architecture (stub, untrained)
  - **iTransformer:** Inverted transformer (stub, untrained)
  - **Ensemble:** Ridge regression meta-learner stacking all 3 trained models
- Training engine with GPU/CPU auto-detection, early stopping, ReduceLROnPlateau
- PhysicsValidator safety layer (clamp rainfall ≥0, Tmin ≤ Tmax, temp [-10, 55])

### Phase 4 — Digital Twin Core Engine
- `ClimateEntity` dataclass with immutable update_state and geo-climate validation
- `StateManager` with strict append-only versioning (up to 1000 versions/entity)
- `ParquetRepository` with snappy compression and in-memory caching
- `EventBus` pub/sub system with 5 event types
- `DigitalTwinEngine` central orchestrator with repository rehydration
- `TwinAPI` contract with `TwinEngineAdapter` for downstream consumption

### Phase 5 — Geospatial Dashboard
- **7-page Streamlit dashboard:**
  1. Climate Overview (interactive Folium map, current conditions, district stats)
  2. Forecast Viewer (forecast map, confidence bands, CSV download)
  3. Digital Twin State (current/historical/forecast/version tabs)
  4. Scenario Simulator (presets + custom sliders, before/after comparison)
  5. Climate Risk (heat map, district ranking, SHAP waterfall, risk trends)
  6. Reports & Insights (district summaries, data explorer, report generation)
  7. (Implicit) Copilot Chat (via `/ask` API from dashboard)
- Plotly charts (time series, comparison, distribution, risk trends)
- Folium maps (climate overlays, district boundaries, risk heatmaps, delta maps)
- `DashboardAPI` client with synthetic data fallback for all endpoints

### Phase 6 — Scenario Simulation Engine
- 5 scenario types: temperature (±1-3°C), rainfall (±10-40%), monsoon (delay/advance), extreme events (flood/heatwave/drought), combined
- 11 preset scenario definitions
- Deterministic execution (<3s hard limit)
- Input validation with YAML-configured bounds
- Output generation (JSON, CSV, Markdown)
- Event publishing (6 scenario event types)

### Phase 7 — Climate Risk & Explainable AI
- 4 risk types: Heat (0-40), Flood (0-40), Drought (0-35), Composite (weighted)
- 5 risk categories: Very Low (0-20), Low (21-40), Moderate (41-60), High (61-80), Severe (81-100)
- Deterministic SHAP estimation (offline mode, no actual model calls)
- Natural-language climate insights engine
- Full report generation (JSON + Markdown)
- `RiskAPI` abstract contract for downstream consumption

### Phase 8 — RAG Knowledge Base
- FAISS vector store (IndexFlatIP, 384-dim, cosine similarity)
- Sentence transformers (`all-MiniLM-L6-v2`) with deterministic dummy fallback
- Document loaders: Markdown, TXT, CSV, JSON (PDF declared but not implemented)
- Recursive chunking (700 chars, 120 overlap) with metadata inheritance
- Semantic search (top_k=5, score threshold=0.5, metadata filtering)
- 5 indexed documents from government, IMD, ISRO, research, and risk categories
- Indexing pipeline with per-file success/failure tracking

### Phase 9 — Climate Copilot
- Multi-agent architecture: Intent→Planner→Executor→Generator
- 8 intent types: forecast, twin_state, scenario, risk_assessment, rag_query, report, greeting, unknown
- 6 tool implementations with strict contracts (run/validate/describe/health_check)
- LLM integration via Ollama (Qwen3:8b, temperature 0.1, context 8192)
- Conversation buffer memory (10 turns, 60 min expiry)
- 4 prompt templates for intent classification, planning, generation, and error handling

### Phase 10 — DevOps & Deployment
- All 8 Dockerfiles rewritten with HEALTHCHECK and pinned dependencies
- Docker Compose with env interpolation, port configurability, health conditions
- Prometheus + Grafana monitoring stack with pre-configured dashboards
- CI/CD: GitHub Actions (lint, test matrix, Docker build, deploy on version tags)
- Deployment scripts: startup, shutdown, health check (shell + Python), demo
- Nginx reverse proxy configuration (WebSocket support for Streamlit)
- `Makefile` with 12 targets
- Comprehensive README with architecture diagram and quick start

---

## Known Issues

### 18 Known Test Failures (Environment-Related)

All 18 failures are caused by dependency version mismatches in the local development environment — they do not affect Docker-based deployment.

| Group | Count | Root Cause | Resolution Target |
|---|---|---|---|
| A | 1 | NumPy 2.x removed `np.long`, breaking SciPy→Plotly chain | Sprint 6 (Deployment Hardening) |
| B | 1 | Streamlit/Starlette version mismatch (`DEFAULT_EXCLUDED_CONTENT_TYPES`) | Sprint 6 |
| C | 16 | FAISS built for NumPy 2.x imports `numpy._core` (not in NumPy 1.26) | Sprint 6 |

### Service Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| RAG service unavailable outside Docker | FAISS/numpy version conflict on local env | Run via Docker only |
| RAG falls back to synthetic data outside Docker | No real document retrieval | Deploy with Docker |
| Training data limited to 2011 (not 1981-2023) | Reduced temporal coverage | Update data sources |
| Grid bounds minor offset (lon=79, doc says 78.5) | Minor coordinate shift | Acceptable for POC |
| No authentication on any endpoint | Security gap | Hackathon-only deployment |
| No PDF loader for RAG | Cannot index PDF documents | Convert to Markdown first |

---

## Installation

### Prerequisites
- Docker 20.10+ & Docker Compose 2.x
- Python 3.10+ (for local dev only)

### Quick Start

```bash
# Clone
git clone <repo-url> climate-digital-twin
cd climate-digital-twin

# Configure
cp deployment/configs/.env.example .env

# Deploy
docker compose up -d

# Verify health
python deployment/health/health_check.py

# Access
open http://localhost:8501
```

### Demo Walkthrough

```bash
bash deployment/scripts/demo.sh
```

---

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
   ┌─────┐ ┌────┐ ┌────┐ ┌─┴┐ ┌──┴┐ ┌──┴┐ ┌──────────┐
   │Twin │ │Fore│ │Scen│ │Rsk│ │RAG│ │Copl│ │  Ollama  │
   │Core │ │cast│ │Eng │ │Eng│ │Svc│ │Agnt│ │  11434   │
   │8001 │ │8006│ │8002│ │800│ │800│ │8005│ └──────────┘
   └─────┘ └────┘ └────┘ └───┘ └───┘ └────┘
```

**Tech Stack:** PyTorch, FastAPI, Streamlit, FAISS, Sentence-Transformers, Ollama (Qwen3:8b), DuckDB, Prometheus, Grafana
