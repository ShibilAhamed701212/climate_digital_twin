# Judge Demo Script — 5 Minutes

> **⚠️ Honest version. All data is synthetic. Copilot returns mock responses. Not production-ready.**

---

## 0:00–0:30 — Problem Statement

**Speaker:**
"Good morning/afternoon, judges. India is a climate-vulnerable nation where 60% of agriculture depends on monsoon rainfall. Yet, localized climate forecasting remains a challenge. Today, we present a **proof-of-concept** AI-powered Digital Twin of India's Climate — a system that demonstrates the architecture for predicting rainfall and temperature, simulating climate scenarios, assessing risk, and answering natural language queries. Our pilot region is Karnataka, with 15 sample districts. **I want to be upfront: this is a working prototype built for this hackathon. All data shown is synthetic — we prioritized building the full pipeline over real data integration in the 6-week timeframe.** "

---

## 0:30–1:30 — Architecture

**Speaker:**
"Our system runs 8 Docker services:

1. **Data Pipeline** — generates synthetic climate data matching NASA POWER schema
2. **Forecast Engine** — 7 model architectures defined, 3 trained (MLP, LSTM, Transformer) on synthetic data
3. **Digital Twin Core** — immutable state management with append-only versioning — the strongest component
4. **Scenario Engine** — deterministic what-if simulation with 11 presets
5. **Risk Engine** — heat, flood, drought, and composite scoring
6. **RAG Knowledge Base** — FAISS vector store indexing 15 demo documents (~30 chunks)
7. **Climate Copilot** — intent classification → tool dispatch → **mock response** (no LLM wired yet)
8. **Dashboard** — Streamlit app with 7 live pages + 3 placeholder pages

The 8th service is an Nginx gateway. Ollama is available in the compose file but not yet connected to the copilot."

---

## 1:30–2:30 — Demo

**Speaker:**
"Let me show you the system running. [OPEN DASHBOARD]

**Climate Overview** — Interactive map of Karnataka showing synthetic temperature and rainfall. Data is generated with numpy random seed — looks realistic but is not real observations.

**Forecast Viewer** — 7-day predictions from our LSTM model. RMSE 4.53 on the synthetic test set — but this metric is only meaningful relative to other models in our benchmark, not as absolute accuracy.

**Twin State** — This is our digital twin with versioned state. Every update creates a new immutable version — this design is production-quality.

**Scenario Simulator** — Applying a +2°C temperature increase. The engine computes deltas per district in <3 seconds deterministically.

**Climate Risk** — Heatmap of composite risk. Scores are computed using configurable weighted formulas — the methodology is sound but uncalibrated against real hazard events.

**Copilot** — I can ask about forecasts or risks. **The responses are template-based.** We designed the 4-stage pipeline (Intent→Plan→Execute→Generate) but haven't wired the LLM yet. The architecture is ready — the LLM integration is the next step."

---

## 2:30–3:30 — Technical Details

**Speaker:**
"Here's what we built in 6 weeks:

| Component | Lines of Code | Status |
|-----------|--------------|--------|
| Digital Twin | ~800 | Most complete |
| Forecasting Models | ~2,000 | 3 trained on synthetic, 3 stubs |
| Scenario Engine | ~500 | Deterministic, <3s |
| Risk Engine | ~600 | 4 modules, configurable |
| RAG Pipeline | ~600 | FAISS, 30 chunks, mock answers |
| Copilot | ~500 | 4-stage pipeline, mock responses |
| Dashboard | ~3,000 | 7 live pages + 3 mock |
| Tests | ~109 passing | 18 known env failures |

The LSTM model achieves RMSE 4.53 on synthetic data — but all three trained models show R²=0.87, which tells us the synthetic data is too simple to differentiate model architectures. **Real data would produce different results.** "

---

## 3:30–4:00 — RAG & Copilot (Honest)

**Speaker:**
"Our RAG knowledge base indexes 15 documents (30 chunks) in a FAISS vector store. Retrieval works with <3ms latency on this small index. However, **the `generate_answer()` function returns template responses, not LLM-generated answers.** The FAISS index also starts empty — documents must be indexed explicitly on first run.

The copilot uses keyword-based intent classification. It dispatches to real API endpoints for forecast and risk data, but the response is assembled from templates. We designed the architecture to plug in Qwen3:8b via Ollama — that integration is the next priority."

---

## 4:00–4:30 — Deployment

**Speaker:**
"All services are containerized with Docker Compose:

- 8 Dockerfiles with pinned Python dependencies
- Nginx reverse proxy
- Health check endpoints on every service
- One-command startup: `docker compose up`

**This is a local demo deployment.** We have no production deployment, no authentication, no HTTPS, no load testing. For a production system you would need authentication, real data, real LLM, proper test coverage, and monitoring."

---

## 4:30–5:00 — Impact & Roadmap

**Speaker:**
"The architecture demonstrates how a climate digital twin could help farmers, disaster managers, and policymakers. The foundation is solid.

**What's real now:**
- Containerized 8-service deployment
- Synthetic data pipeline end-to-end
- Digital twin with append-only versioning
- Scenario engine with 11 presets
- Risk scoring with configurable weights
- Dashboard with interactive maps and charts

**What comes next:**
- **Real data** — connect NASA POWER / IMD / ISRO APIs (highest priority)
- **Real LLM** — wire Qwen3:8b to the copilot generator
- **Real SHAP** — connect explainability to model gradients
- **Authentication** — add API keys and HTTPS
- **Test coverage** — add tests for models, APIs, RAG, copilot
- **Scale** — Karnataka to all India

This is a **proof-of-concept** that shows the vision works. The pipeline runs. The architecture is sound. The next team can take it from prototype to production.

Thank you. Happy to answer questions."
