# System Overview

> **Hackathon Proof-of-Concept** — All data synthetic. Not production-ready.

---

## 8-Step Pipeline

The following pipeline runs end-to-end on **synthetic data (np.random.seed(42))**:

```
Dataset → Forecast → Digital Twin → Scenario → Risk → RAG → Copilot → Dashboard
```

| Step | Service | Port | Purpose | Honest Status |
|------|---------|------|---------|---------------|
| 1. Dataset | Data Ingestion | (script) | Generate/load synthetic climate data | ✅ Synthetic generation only |
| 2. Forecast | Forecasting API | 8005 | Predict future climate variables | ✅ Predictions on synthetic data |
| 3. Digital Twin | Twin API | 8002 | Maintain climate state | ✅ Synthetic state versioning |
| 4. Scenario | Scenario Engine | 8003 | Apply climate perturbations | ✅ Deterministic deltas |
| 5. Risk | Risk API | 8004 | Compute hazard scores | ✅ Weighted scoring on synthetic data |
| 6. RAG | RAG API | 8006 | Retrieve knowledge base context | ⚠️ FAISS empty by default |
| 7. Copilot | Copilot API | 8007 | Answer natural language queries | ⚠️ Mock responses only |
| 8. Dashboard | Streamlit UI | 8501 | Visualize and interact | ✅ 7 live pages + 3 mock pages |

---

## Microservice Architecture (8 Services)

| Service | Build Context | Docker Image | Depends On | Honest Status |
|---------|--------------|--------------|------------|---------------|
| Gateway | nginx-gateway | nginx:alpine | All services | ✅ Routes to all services |
| Forecasting API | ./api | climate-api | — | ✅ Synthetic predictions |
| Twin API | ./digital_twin | climate-twin | — | ✅ Synthetic state |
| Scenario Engine | ./scenario_engine | climate-scenario | twin-api | ✅ Deterministic <3s |
| Risk API | ./risk | climate-risk | — | ✅ Synthetic scores |
| RAG API | ./rag | climate-rag | — | ⚠️ Empty index |
| Copilot API | ./copilot | climate-copilot | — | ⚠️ Mock responses |
| Dashboard | ./app | climate-dashboard | All APIs | ✅ 10 pages |

**Note:** Ollama is a separate container dependency for future LLM integration. Currently not wired to the copilot service.

---

## Tech Stack

### Machine Learning
- **Framework:** PyTorch 2.0+
- **Models:** MLP, LSTM, Transformer (trained on synthetic data)
- **Stubs:** PatchTST, TimeMixer, iTransformer (class definitions only)
- **Ensemble:** Ridge regression meta-learner (mock)

### Backend
- **API Framework:** FastAPI + Uvicorn
- **Vector Store:** FAISS (IndexFlatIP, 384-dim)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Storage:** Parquet + DuckDB

### Frontend
- **Dashboard:** Streamlit + Plotly + Folium

### Infrastructure
- **Orchestration:** Docker Compose
- **Monitoring:** Prometheus + Grafana (defined but not actively used)

---

## Pilot Scope

| Dimension | Value |
|-----------|-------|
| Geographic scope | 15 sample Karnataka districts (hardcoded in config) |
| Data source | Synthetic (no real API calls) |
| Time period | Simulated 43-year range (1981–2023) |
| Grid resolution | 48 synthetic grid cells |
| Feature count | 12 engineered features |
| Model architectures | 7 defined, 3 trained |
| Scenario presets | 11 (temperature ±1–3°C, rainfall ±10–40%) |
| Risk categories | Heat, Flood, Drought, Composite |

---

## Key Constraints

1. **All data is synthetic.** No real climate observation from NASA POWER, IMD, or ISRO was ever ingested. The download pipeline exists but falls back to synthetic generation on any failure.
2. **FAISS index starts empty.** Vector store must be populated on first run from 15 bundled documents (PDF stubs, markdown, CSV). `generate_answer()` returns mock responses.
3. **Copilot is a mock.** The intent classification, planner, executor, and generator stages exist in code but the LLM call to Qwen3:8b is stubbed. All responses are template-based.
4. **Dashboard has 3 mock pages.** Pages 08 (Knowledge Base), 09 (Feedback), and 10 (BHAI State) display hardcoded placeholder content with no backend connectivity.
5. **18 test failures are expected.** Due to NumPy/FAISS/Streamlit version incompatibilities in certain environments. Not indicative of code bugs.
6. **No authentication.** All endpoints are open. No RBAC, no API key validation, no rate limiting.
