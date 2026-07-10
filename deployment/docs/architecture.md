# Climate Digital Twin — Architecture

## Overview

An AI-powered Digital Twin of India's climate system, built for ISRO BAH 2026 (Challenge 5). The system predicts rainfall and temperature, simulates future climate scenarios, assesses climate risk with explainable AI, and provides natural-language climate intelligence via a Copilot agent.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    streamlit-dashboard                   │
│                       Port 8501                          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    fastapi-gateway                        │
│                       Port 8000                           │
└──┬──────┬──────┬──────┬──────┬──────┬───────────────────┘
   │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼
┌─────┐ ┌────┐ ┌──────┐ ┌────┐ ┌────┐ ┌──────────────┐
│Twin │ │Fore│ │Scen. │ │Risk│ │RAG │ │Copilot Agent │
│Core │ │cast│ │Engine│ │Eng.│ │Svc │ │   Port 8005   │
│8001 │ │    │ │8002  │ │8003│ │8004│ └──────────────┘
└─────┘ └────┘ └──────┘ └────┘ └────┘
```

## Service Descriptions

| Service | Port | Description |
|---------|------|-------------|
| **twin-state-mgr** | 8001 | Digital Twin engine — entity model, state manager, versioning, event system, parquet repository |
| **forecast-engine** | — | ML forecasting — MLP, LSTM, Transformer models for rainfall/temperature prediction |
| **scenario-engine** | 8002 | What-if simulation — temperature, rainfall, monsoon, extreme event scenarios |
| **risk-engine** | 8003 | Climate risk assessment — heat, flood, drought, composite scoring with SHAP explainability |
| **rag-service** | 8004 | RAG knowledge base — FAISS vector store, semantic search, document indexing |
| **copilot-agent** | 8005 | Climate Copilot — multi-agent orchestration (Intent→Planner→Executor→Generator) |
| **fastapi-gateway** | 8000 | API Gateway — routes requests to all downstream services |
| **streamlit-dashboard** | 8501 | Interactive dashboard — 6 pages with Plotly charts, Folium maps, risk panels |

## Data Flow

1. **User interacts** with the Streamlit Dashboard (or directly with the API Gateway)
2. **API Gateway** routes requests to the appropriate service
3. **Twin State Manager** maintains the canonical state of all climate entities
4. **Forecast Engine** uses historical data + ML models to predict future conditions
5. **Scenario Engine** modifies baseline conditions for what-if analysis
6. **Risk Engine** computes risk scores and SHAP explanations
7. **RAG Service** indexes and retrieves climate documents via semantic search
8. **Copilot Agent** classifies intent, plans tool calls, executes, and generates natural-language responses

## Technology Stack

- **ML Framework:** PyTorch
- **Backend:** FastAPI + Uvicorn
- **Dashboard:** Streamlit + Plotly + Folium
- **Vector Store:** FAISS
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **LLM:** Qwen 3 4B (via Ollama)
- **Storage:** Parquet + DuckDB
- **Containerization:** Docker + Docker Compose
- **Monitoring:** Prometheus + Grafana
- **CI/CD:** GitHub Actions

## Offline Demo Mode

All services include synthetic data fallback for offline/hackathon environments:
- Pre-cached models with deterministic predictions
- Synthetic climate data generation
- Dummy embedding fallback for FAISS
- Deterministic SHAP estimation
- No external API dependencies required
