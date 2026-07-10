# Judge Demo Script — 5 Minutes
## AI-Powered Digital Twin of India's Climate
### ISRO BAH 2026 — Challenge 5

---

## 0:00–0:30 — Problem Statement

**Speaker:**
"Good morning/afternoon, judges. India is a climate-vulnerable nation where 60% of agriculture depends on monsoon rainfall. Yet, localized climate forecasting remains a challenge. Today, we present an AI-powered Digital Twin of India's Climate — a proof-of-concept system that predicts rainfall and temperature, simulates climate scenarios, assesses risk, and answers natural language queries about climate conditions. Our pilot region is Karnataka, spanning 5 districts: Bengaluru Urban, Mysuru, Belagavi, Dakshina Kannada, and Kalaburagi."

---

## 0:30–1:30 — Architecture

**Speaker:**
"Our system is built on a 9-microservice architecture orchestrated via Docker Compose. The data flows through an 8-step pipeline:

1. **Data Pipeline** — ingests 43 years of NASA POWER climate data (1981–2023) at 0.25° grid resolution, engineered into 11 features with 14 total columns
2. **Forecast Engine** — 7 model architectures including LSTM, Transformer, and ensemble meta-learner
3. **Digital Twin Core** — immutable state management with append-only versioning and pub/sub event system
4. **Scenario Engine** — deterministic what-if simulation with 11 presets and 5 scenario types
5. **Risk Engine** — heat, flood, drought, and composite scoring with SHAP explainability
6. **RAG Knowledge Base** — FAISS vector store with semantic search over 15 sources
7. **Climate Copilot** — multi-agent LLM orchestration (Intent->Plan->Execute->Generate)
8. **Dashboard** — 7-page Streamlit app with interactive Folium maps and Plotly charts

All services have health checks, synthetic data fallback for offline operation, and communicate through a FastAPI gateway."

---

## 1:30–2:30 — Demo

**Speaker:**
"Let me show you the live system. [OPEN DASHBOARD]

**Climate Overview** — Here's our interactive map of Karnataka, showing current temperature and rainfall conditions across the state. We have 40 grid cells at 0.5° resolution.

**Forecast Viewer** — Switching to the forecast page, we can see 7-day predictions for any location. The LSTM model — our best performer — generates predictions with 95% confidence intervals.

**Twin State** — This page shows the digital twin's current state, historical data, and version timeline. Every observation is immutably versioned.

**Scenario Simulator** — Here I can simulate what-if scenarios. Let's apply a +2°C temperature increase. The engine computes deltas per location, showing practical impacts.

**Climate Risk** — The risk page shows a heatmap of composite risk across Karnataka. Our system scores heat, flood, drought, and composite risk on a 0–100 scale.

**Copilot** — Finally, the AI Copilot. I can ask: 'What's the weather forecast for Bengaluru?' or 'What are the flood risks in Mysuru?' — and the multi-agent system classifies the intent, plans tool calls, executes, and generates a response."

---

## 2:30–3:30 — Scientific Validation

**Speaker:**
"Let's talk numbers. We trained 3 model architectures on 628,200 processed data points:

| Model | RMSE | R² | Parameters | Checkpoint |
|-------|------|-----|-----------|------------|
| LSTM | **4.53** | 0.87 | 203K | 802 KB |
| Transformer | 4.57 | 0.87 | 596K | 2,847 KB |
| Baseline MLP | 4.59 | 0.87 | 21K | 94.5 KB |

All three models achieve R² of 0.87. The LSTM is our best performer with RMSE 4.53. The Transformer is the fastest at inference — 26.8 ms total, 69x faster than baseline.

We also implemented an ensemble meta-learner using Ridge regression that stacks all base model predictions. Three additional architectures — PatchTST, TimeMixer, and iTransformer — are implemented as stubs for future training.

The PhysicsValidator safety layer ensures all predictions are physically plausible: rainfall ≥ 0, Tmin ≤ Tmax, temperatures clamped to [-10, 55]°C."

---

## 3:30–4:00 — RAG Knowledge Base

**Speaker:**
"Our RAG knowledge base indexes 15 documents from 5 source categories: government (Karnataka climate profile), ISRO (INSAT satellite products), IMD (weather data), research (forecasting methods), and risk assessment. Documents are chunked at 700 tokens with 120-token overlap, embedded using all-MiniLM-L6-v2 (384-dimensional vectors), and stored in a FAISS IndexFlatIP vector store.

The system handles 30 indexed chunks with retrieval latency under 3 ms. Across 8 benchmark queries, we achieved 100% retrieval rate with mean top score of 0.659.

The KnowledgeAPI supports index, search, delete, list, rebuild, and retrieve_context operations — all wrapped into the RAG Service on port 8004."

---

## 4:00–4:30 — Deployment

**Speaker:**
"All 9 microservices are containerized with Docker and orchestrated via Docker Compose. Each service has:
- A dedicated Dockerfile with pinned dependencies
- HEALTHCHECK instructions with 10-second intervals
- Dependency ordering via depends_on conditions

The deployment includes:
- 8 application Dockerfiles (gateway, dashboard, twin, forecast, scenario, risk, RAG, copilot)
- Prometheus (port 9090) for metrics collection
- Grafana (port 3000) with a provisioned 6-panel service health dashboard
- Nginx reverse proxy for routing
- Pre-configured .env file with 14 variables

CI/CD pipelines via GitHub Actions handle linting, testing (matrix 3.10/3.12), Docker builds, and CD on version tags.

We also have shell and Python health check utilities, a one-click startup script, and a demo walkthrough script."

---

## 4:30–5:00 — Societal Impact & Roadmap

**Speaker:**
"The societal impact is significant. India loses 3-5% of GDP annually to climate-related disasters. A system like this can:
- Help farmers plan sowing and irrigation with 7-day forecasts
- Enable district-level disaster preparedness with risk scores
- Support policy planning with what-if scenario analysis
- Democratize climate intelligence through the AI Copilot

**Future roadmap:**
- **National scale-up** — extend from Karnataka to all Indian states
- **Real SHAP** — connect explainability to model gradients instead of synthetic estimation
- **Advanced models** — train PatchTST, TimeMixer, iTransformer architectures
- **Real-time data** — integrate live IMD and INSAT feeds
- **Mobile app** — farmer-facing notifications for extreme weather alerts

Thank you. We're happy to take questions."
