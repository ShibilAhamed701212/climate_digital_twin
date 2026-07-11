# Presentation Outline — 20 Slides

> **⚠️ Honest version. Synthetic data. Proof-of-concept.**

---

## Section 1: Problem & Motivation (Slides 1–3)

### Slide 1: Title Slide
- Project: AI-Powered Digital Twin of India's Climate
- ISRO BAH 2026 — Challenge 5
- **Proof-of-concept** — synthetic data, mock copilot
- Tagline: *From Architecture to Impact: A Climate Digital Twin Prototype*

### Slide 2: The Climate Challenge
- India: 3-5% GDP lost annually to climate disasters
- 60% agriculture dependent on monsoon
- Problem: Data exists but is fragmented, not localized, not actionable
- Pilot focus: Karnataka — 15 districts in config
- **Honest:** We built the architecture. Data integration is next.

### Slide 3: Solution Overview
- AI-powered Digital Twin of India's Climate (Prototype)
- 8 Docker services, 8-step data pipeline
- 3 trained model architectures (on synthetic data)
- RAG knowledge base + mock AI Copilot
- Docker Compose deployment

---

## Section 2: Architecture & Design (Slides 4–6)

### Slide 4: System Architecture Diagram
- 8-service Docker Compose architecture
- Gateway → 6 backend services + Dashboard
- Monitoring: Prometheus + Grafana (defined, not configured)
- **Honest:** No auth, no HTTPS, no production hardening

### Slide 5: Data Flow Pipeline
- 8-step pipeline: Dataset → Forecast → Digital Twin → Scenario → Risk → RAG → Copilot → Dashboard
- **All steps on synthetic data**
- Every API call has synthetic fallback
- Data flows through with deterministic results

### Slide 6: Tech Stack
- ML Framework: PyTorch 2.0+
- Backend: FastAPI + Uvicorn
- Dashboard: Streamlit + Plotly + Folium
- Vector Store: FAISS (IndexFlatIP) — starts empty
- Embeddings: sentence-transformers (all-MiniLM-L6-v2)
- LLM: Qwen3:8b via Ollama (⚠️ NOT wired)
- Explainability: Deterministic synthetic SHAP
- Storage: Parquet + DuckDB
- Monitoring: Prometheus + Grafana (⚠️ not configured)

---

## Section 3: Data Pipeline & Models (Slides 7–9)

### Slide 7: Data Pipeline (Honest)
- **Declared:** NASA POWER API (1981-2023)
- **Actual:** `np.random.seed(42)` synthetic generation
- Pipeline: Download → Validate → Clean → Feature Engineering → Export
- 12 engineered features
- 628,200 synthetic rows, 70/15/15 split
- **API integration exists but always falls back to synthetic**

### Slide 8: Forecasting Models
- 7 model architectures: 3 trained, 3 stubs, 1 mock ensemble
- Trained: MLP (RMSE 4.59), LSTM (RMSE 4.53), Transformer (RMSE 4.57)
- Stubs: PatchTST, TimeMixer, iTransformer
- **All metrics on synthetic data only**
- PhysicsValidator enforces basic constraints

### Slide 9: Training & Evaluation
- Sliding window of 30 days, batch size 64
- Adam optimizer, MSE loss, ReduceLROnPlateau scheduler
- Early stopping (patience 10)
- **All three models show suspiciously uniform R²=0.87**
- **No hyperparameter optimization performed**

---

## Section 4: Digital Twin & Scenarios (Slides 10–12)

### Slide 10: Digital Twin Core
- Immutable ClimateEntity dataclass with geo-climate validation
- StateManager: Append-only versioning
- EventBus: Pub/sub with 5 event types
- Parquet storage per location
- **Cleanest component of the system — production-quality design**

### Slide 11: Scenario Simulation Engine
- 5 scenario types, 11 preset scenarios
- Deterministic execution < 3 seconds
- Physics constraints enforced
- **All scenarios modify synthetic baseline**

### Slide 12: Scenario Examples & Visuals
- Before/after comparison maps
- Example: +2°C temperature scenario across Karnataka districts
- Example: -25% rainfall scenario impact
- **Results are delta-from-synthetic**

---

## Section 5: Risk & Explainability (Slides 13–14)

### Slide 13: Climate Risk Engine
- 4 modules: Heat, Flood, Drought, Composite (0–100)
- Configurable weights from risk.yaml
- 5 categories: Very Low to Severe
- **Risk thresholds arbitrary — not calibrated against real events**

### Slide 14: SHAP Explainability
- ⚠️ **Deterministic synthetic SHAP** — not from model gradients
- Per-feature contribution values (position-based)
- Template natural-language insights
- **SHAP integration with model gradients is future work**

---

## Section 6: RAG & Copilot (Slides 15–16)

### Slide 15: RAG Knowledge Base
- FAISS IndexFlatIP (384-dim)
- 15 documents, ~30 chunks (tiny demo)
- 5 format loaders: MD, TXT, CSV, JSON, PDF (stub)
- ⚠️ **Index starts empty** — must be populated
- ⚠️ **`generate_answer()` returns mock responses**

### Slide 16: AI Climate Copilot
- 4-step pipeline: Intent → Plan → Execute → Generate
- 8 intent types (keyword classification)
- ⚠️ **All responses are template-based (mock)**
- ⚠️ **Qwen3:8b declared but never wired**
- Conversation memory: 10 turns, 60min expiry

---

## Section 7: Results & Validation (Slides 17–18)

### Slide 17: Testing Metrics (Honest)
- **109 tests passing** (dashboard-focused)
- **18 known environment-related failures**
- **0% coverage** for models, API, RAG, copilot code
- Previous "656 tests" claim corrected
- 17/17 pipeline stages pass (on synthetic data)

### Slide 18: Architecture Assessment
- **Not production-ready**
- No authentication — all endpoints open
- No real data ever ingested
- No LLM integration
- **Architecture is sound — execution is a prototype**

---

## Section 8: Future & Impact (Slides 19–20)

### Slide 19: Path to Impact
- Architecture works end-to-end on synthetic data
- Digital twin core is production-quality
- Containerized deployment ready to extend
- **Real data ingestion is #1 priority**
- **LLM integration is #2 priority**

### Slide 20: Roadmap
- **Phase 1 (Q3):** Real data from NASA POWER/IMD/ISRO
- **Phase 2 (Q3):** Wire LLM to copilot
- **Phase 3 (Q4):** Authentication, HTTPS, rate limiting
- **Phase 4 (2027):** Scale from Karnataka to all India
- **Phase 5:** Train stubs, real SHAP, mobile app, decision intelligence

---

## Appendix: Backup Slides

### A1: Detailed Model Architectures (3 trained, 3 stubs, 1 mock)
### A2: API Endpoint Reference
### A3: Configuration YAML Reference
### A4: Docker Compose Service Definitions
### A5: E2E Test Methodology (on synthetic data)
### A6: Lessons Learned from 6-Week Hackathon Sprint
