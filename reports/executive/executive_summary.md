# Executive Summary — AI-Powered Digital Twin of India's Climate

> **ISRO BAH 2026 — Challenge 5**  
> **Hackathon Proof-of-Concept (v0.1.0)**  
> **Built:** May–June 2026 (~6 weeks)  
> **Honest Status:** Functional demonstrable prototype. All data synthetic. Not production-ready.

---

## What This Project Is

A proof-of-concept digital twin for climate resilience in Karnataka, India. The system demonstrates an 8-step pipeline from data ingestion → forecasting → simulation → risk assessment → RAG-powered Q&A → interactive dashboard. Every component is containerized with Docker Compose and can be demonstrated end-to-end — **on synthetic data.**

## What This Project Is NOT

- ❌ **Not validated on real climate data.** All .parquet/.csv files are `np.random.seed(42)` synthetic.
- ❌ **Not production-ready.** No authentication, no real API keys, no load testing, no SLAs.
- ❌ **Not connected to real LLMs.** Copilot returns mock responses. Qwen3:8b is declared but not wired.
- ❌ **Not a complete 9-microservice system.** 8 Docker services; Ollama is a dependency, not a custom service.
- ❌ **Not 656 tests passing.** 109 dashboard tests pass; 18 known env-related failures.

---

## Architecture Overview

| Component | Technology | Honest Status |
|-----------|-----------|---------------|
| Backend API | FastAPI (Python 3.11) | ✅ 6 endpoints work with synthetic fallback |
| Dashboard | Streamlit + Plotly + Folium | ✅ 7 live pages + 3 mock pages |
| Forecasting | PyTorch (MLP/LSTM/Transformer) | ✅ 3 trained on synthetic data, 3 stubs |
| Digital Twin | Python dataclass + event bus | ✅ Clean design, populated with synthetic states |
| Risk Engine | Weighted scoring (0–100) | ✅ 4 modules, configurable, all on synthetic data |
| RAG | FAISS + sentence-transformers | ⚠️ Index starts empty; ~30 chunks from 15 docs |
| Copilot | Keyword classification → mock response | ⚠️ No real LLM integration |
| Explainability | Deterministic synthetic SHAP | ⚠️ Not connected to model gradients |
| Scenario Engine | 5 types, 11 presets | ✅ <3s deterministic, synthetic baseline |

---

## Key Metrics (On Synthetic Data Only)

| Metric | Value | Caveat |
|--------|-------|--------|
| LSTM RMSE | ~4.53 mm/day | On synthetic rainfall. Real performance unknown. |
| Models at R²=0.87 | 3 of 3 trained | Suspiciously uniform — expected on synthetic data. |
| Pipeline stages passing | 17/17 | End-to-end synthetic run. |
| Dashboard tests passing | 109 | Excluding 18 known env failures. |
| Total Python LOC | ~17,354 | Includes models, tests, generated files, legacy code. |
| Docker services | 8 | + Ollama dependency (manual model pull required). |
| Training time (LSTM) | ~2 min on synthetic data | Single epoch batch, no hyperparameter tuning. |

---

## Codebase Structure (Key Directories)

```
climate-digital-twin/
├── app/                    # Streamlit dashboard
├── api/                    # FastAPI backend
├── models/                 # PyTorch forecasting models
├── digital_twin/           # Digital twin core
├── scenario_engine/        # Scenario simulation
├── risk/                   # Risk scoring engine
├── rag/                    # FAISS RAG pipeline
├── copilot/                # Mock copilot
├── explainability/         # Deterministic SHAP
├── config/                 # YAML/JSON configuration
├── data/                   # Synthetic data storage
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── tools/                  # Development tools
├── reports/                # This documentation
└── docker/                 # Docker configuration
```

---

## What Works (Honest Assessment)

- **Docker Compose up** launches all 8 services successfully (conditional on Ollama model availability)
- **Data pipeline** generates synthetic data and runs through all 8 stages
- **Dashboard** renders interactive charts, maps, and tables with synthetic data
- **Forecasting** trains 3 models and generates predictions (on synthetic data)
- **Scenario engine** applies deltas and returns results in <3 seconds
- **Risk scores** compute per-district heat/flood/drought/composite on synthetic data
- **109/127 tests pass** (18 env-related failures pre-existing)

## What Does NOT Work

- **Real data ingestion** — never connected to NASA POWER/IMD/ISRO APIs
- **LLM-powered Copilot** — mock responses only
- **RAG retrieval from real documents** — FAISS index starts empty
- **Authentication/authorization** — none implemented
- **Production deployment** — not load tested, not hardened
- **Real SHAP** — synthetic values, not from model gradients

---

## Conclusion

This project is a **successful hackathon proof-of-concept** that demonstrates the architecture, pipeline, and UI for a climate digital twin. The design is modular, containerized, and demonstrable. The critical next step — replacing synthetic data with real observations and wiring real LLM integration — remains uncompleted. The codebase provides a solid foundation for future development but is **not production ready** in its current state.
