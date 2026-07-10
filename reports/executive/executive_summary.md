# Executive Summary — Climate Digital Twin

## Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | AI-Powered Digital Twin of India's Climate |
| **Repository** | `climate-digital-twin` |
| **Hackathon** | ISRO BAH 2026 — Challenge 5 |
| **Version** | 0.1.0 |
| **Pilot Region** | Karnataka (11.5–18.5°N, 74.0–78.5°E) |

## Problem Statement

Develop a proof-of-concept AI-powered Digital Twin of India's climate system using national datasets. The system must predict rainfall and temperature, simulate future climate scenarios, visualize conditions via an interactive dashboard, and support climate intelligence queries through an AI assistant. The pilot is scoped to Karnataka state with 5 pilot districts: Bengaluru Urban, Mysuru, Belagavi, Dakshina Kannada, and Kalaburagi.

## Architecture Overview

9 microservices orchestrated via Docker Compose:

| Service | Port | Role |
|---------|------|------|
| Twin State Manager | 8001 | Entity state, versioning, event system |
| Scenario Engine | 8002 | What-if simulation |
| Risk Engine | 8003 | Climate risk scoring + SHAP explainability |
| RAG Service | 8004 | FAISS vector store + semantic search |
| Copilot Agent | 8005 | Multi-agent LLM orchestration |
| Forecast Engine | 8006 | ML forecasting |
| API Gateway | 8000 | FastAPI routing |
| Streamlit Dashboard | 8501 | 7-page interactive dashboard |
| Ollama | 11434 | Local LLM serving (Qwen3:8b) |

Plus Prometheus (9090) and Grafana (3000) for monitoring.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Framework | PyTorch 2.0+ |
| Forecasting Models | Baseline (MLP), LSTM, Transformer, iTransformer, PatchTST, TimeMixer, Ensemble Meta-Learner |
| Backend | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly + Folium |
| Vector Store | FAISS (IndexFlatIP) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| LLM | Qwen3:8b via Ollama |
| Explainability | SHAP (deterministic offline estimation) |
| Storage | Parquet + DuckDB |
| Monitoring | Prometheus + Grafana |

## Key Metrics

| Metric | Value |
|--------|-------|
| **Total Tests** | 656 |
| **Unit Tests** | ~620 |
| **Integration Tests** | ~36 |
| **E2E Pipeline Stages** | 17/17 passing |
| **Forecasting Models** | 7 architectures |
| **Best RMSE** | 4.53 (LSTM) |
| **RMSE Range** | 4.53–4.59 |
| **R² Score** | 0.87 (all 3 primary models) |
| **Config YAML Files** | 7 externalized |
| **Dockerfiles** | 8 |
| **Dashboard Pages** | 7 |
| **Copilot Tools** | 6 |
| **Risk Categories** | 5 (Very Low → Severe) |
| **Scenario Presets** | 11 |

## Primary Users

- **ISRO BAH 2026 Hackathon Evaluators** — primary audience for demo and evaluation
- **Climate Researchers** — scenario analysis and risk assessment
- **Policy Planners** — district-level climate intelligence via Copilot

## Innovation Summary

The Climate Digital Twin integrates 7 forecasting model architectures, a physics validation safety layer, deterministic SHAP-based explainability, FAISS-powered RAG retrieval from government/ISRO/IMD documents, and a multi-agent LLM Copilot (Intent→Planner→Executor→Generator) — all containerized for one-command deployment with full synthetic data fallback for offline hackathon environments. The system achieves RMSE of 4.53–4.59 mm/°C with R² of 0.87 across rainfall, max temperature, and min temperature predictions for the Karnataka pilot region.
