# Climate Digital Twin — Executive Summary Report

## 1. Project Overview

The **Climate Digital Twin** is an end-to-end AI-powered platform for real-time climate monitoring, hydro-meteorological forecasting, scenario simulation, and multi-hazard risk assessment across India (focused on Karnataka).

It bridges physical hydro-meteorological modeling (evapotranspiration, SCS runoff, SPEI drought classification) with modern deep learning time-series forecasting (LSTM, Transformer, iTransformer, PatchTST, TimeMixer) and conversational RAG AI capabilities.

---

## 2. Key Technical Highlights

| Component | Technical Implementation |
|---|---|
| **Architecture** | 10 containerized microservices orchestrated via Docker Compose & FastAPI |
| **State Management** | Versioned Digital Twin State Manager with history tracking & transaction-safe rollback |
| **Forecasting** | 8 Model Architectures with physics-informed validation & weighted ensemble aggregation |
| **Simulation** | Stochastic Monte Carlo engine with perturbation models (temperature offset, rainfall multiplier) |
| **Risk Scoring** | Automated Heat, Flood, Drought & Composite scoring (0-100) with SHAP explainability |
| **RAG & Knowledge** | FAISS dense semantic + BM25 sparse hybrid retrieval over climate documents |
| **AI Assistant** | Ollama-backed Copilot agent (Qwen 3:4B) with 7 specialized climate tools |
| **Frontend** | 10-page Streamlit dashboard with Plotly visual analytics & Folium spatial mapping |
| **Quality & Tests** | 86% test coverage across 2700+ unit and integration tests |

---

## 3. System Microservices Matrix

```
┌─────────────────────────┬──────┬────────────────────────────────────────────────────────┐
│ Service Name            │ Port │ Primary Functionality                                  │
├─────────────────────────┼──────┼────────────────────────────────────────────────────────┤
│ streamlit-dashboard     │ 8501 │ Interactive 10-page UI for analytics & visualization   │
│ fastapi-gateway         │ 8000 │ Unified REST gateway with CORS, rate limit & docs      │
│ twin-state-mgr          │ 8001 │ Versioned digital twin state repository & synchronizer │
│ scenario-engine         │ 8002 │ Monte Carlo & perturbation scenario simulator          │
│ risk-engine             │ 8003 │ Multi-hazard risk calculator & SHAP explainer          │
│ rag-service             │ 8004 │ FAISS vector store & hybrid document retrieval         │
│ copilot-agent           │ 8005 │ LLM tool-calling conversational agent                  │
│ forecast-engine         │ 8006 │ Multi-model deep learning inference engine             │
│ report-service          │ 8007 │ Automated PDF/Markdown climate report composition      │
│ ollama                  │ 11434│ Local LLM runtime (Qwen 3:4B)                          │
└─────────────────────────┴──────┴────────────────────────────────────────────────────────┘
```
