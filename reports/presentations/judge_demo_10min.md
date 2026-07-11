# Judge Demo Script — 10 Minutes

> **⚠️ Honest version. All data synthetic. Mock copilot. Proof-of-concept.**

---

## 0:00–1:00 — Problem & Motivation

**Speaker:**
"Good morning, judges. India faces a fundamental climate challenge: vast amounts of climate data exist but we lack integrated, localized, actionable climate intelligence.

Our project answers one question: *Can we build the architecture for an AI-powered Digital Twin that integrates forecasting, simulation, risk assessment, and Q&A into a single deployable system?*

We've built a proof-of-concept in 6 weeks. The pipeline runs end-to-end. The architecture is sound. **However, I want to be transparent: this is a prototype. All data is synthetic — generated with numpy random seed. The copilot uses template responses, not a real LLM. We built the full system architecture but real data and real LLM integration remain as next steps.** "

---

## 1:00–2:00 — Architecture Deep Dive

**Speaker:**
"Our architecture consists of 8 Docker services on a shared network:

**Twin State Manager (8002)** — Immutable versioned state. Cleanest component of the system. Types: current, historical, forecast, scenario.

**Forecast Engine (8005)** — 7 model architectures defined. 3 trained on synthetic data (MLP, LSTM, Transformer). 3 are stubs (PatchTST, TimeMixer, iTransformer). Ensemble is not trained.

**Scenario Engine (8003)** — 5 scenario types, 11 presets. Deterministic <3s.

**Risk Engine (8004)** — 4 modules (heat, flood, drought, composite). Configurable weights.

**RAG Service (8006)** — FAISS index with 15 demo documents (~30 chunks). Starts empty.

**Copilot (8007)** — 4-stage pipeline (Intent→Plan→Execute→Generate). **Mock responses.** No LLM wired.

**API Gateway (80)** — Nginx reverse proxy.

**Dashboard (8501)** — 7 live pages + 3 mock placeholder pages.

**Plus:** Ollama container for future LLM integration (Qwen3:8b — not yet connected). Prometheus and Grafana defined but not actively configured."

---

## 2:00–3:00 — Data Pipeline (Honest)

**Speaker:**
"The data pipeline is designed to download from NASA POWER API. In practice, every external call falls back to synthetic data generation:

**Declared source:** NASA POWER API — 3 variables at 0.25°–1.0° resolution.

**Actual source:** `np.random.seed(42)` — all values are random numbers.

**Pipeline stages:**
1. **Generate** — synthetic data matching NASA POWER schema
2. **Validate** — bounds checking (rainfall >= 0, etc.) — passes trivially on generated data
3. **Feature Engineering** — 12 features (temporal, rolling windows, trends)
4. **Export** — 70/15/15 split, Parquet format

**Total:** 628,200 synthetic rows. Zero missing values (expected for generated data).

**Critical honesty:** The NASA POWER API download code exists. It has never successfully executed against a live endpoint. The synthetic fallback is always triggered."

---

## 3:00–4:30 — Models & Forecasting

**Speaker:**
"Our forecasting engine implements 7 model architectures, but only 3 are trained:

**Trained:**
- **MLP** — 3-layer feedforward. RMSE 4.59 on synthetic test set.
- **LSTM** — 2-layer LSTM, hidden 64. **RMSE 4.53** — best on synthetic.
- **Transformer** — 2-layer encoder, d_model=64. RMSE 4.57.

**Stubs (class definitions, no forward pass):**
- PatchTST, TimeMixer, iTransformer

**Mock:**
- Ensemble — Ridge regression wrapper, not trained

**Key observation:** All three trained models show R² = 0.87. This uniformity is suspicious. It tells us the synthetic data is too simple — any model with sufficient capacity learns the same patterns. **Real data would differentiate these architectures.**

**Training details:** Sliding window 30 days, batch 64, Adam, MSE loss, ReduceLROnPlateau, early stopping patience 10. Training takes ~2–3 minutes on synthetic data.

**PhysicsValidator** enforces: rainfall >= 0, Tmin <= Tmax, temperature within [-10, 50]°C."

---

## 4:30–5:30 — Digital Twin & Scenario Engine

**Speaker:**
"The Digital Twin Core is the system's strongest component.

**ClimateEntity** — Immutable frozen dataclass with geo-climate validation. Production-quality design.

**StateManager** — Append-only versioning. Rollback creates new version (no history destruction). Version history per-location.

**EventBus** — Pub/sub with 5 event types. In-memory (not persisted).

**Current limitation:** All states are synthetic. The versioning works correctly but has never seen real data.

**Scenario Engine** — 11 presets: +1/+2/+3°C, -1/-2°C, +10/+25/+40% rain, -10/-25/-40% rain. Deterministic <3 seconds. Physics constraints enforced.

**Limitation:** Scenarios are linear perturbations of synthetic baseline. No spatial correlation. No temporal dynamics. Not calibrated against climate models."

---

## 5:30–6:30 — Risk Engine & Explainability

**Speaker:**
"The Risk Engine provides climate hazard scoring:

**Heat Risk (0–100):** Max temp 40%, hot days 35%, anomaly 25%.
**Flood Risk (0–100):** Intensity 40%, accumulation 35%, uncertainty 25%.
**Drought Risk (0–100):** Deficit 40%, temp increase 30%, dry period 30%.
**Composite:** Weighted average with configurable coefficients.

**Categories:** Very Low (0–20) to Severe (81–100).

**SHAP Explainability:** **The SHAP values are deterministic synthetic estimates, not connected to model gradients.** Each feature gets a position-based weight. The natural-language insights are template strings.

**Limitations:** Risk thresholds are arbitrary. No calibration against real hazard events. No spatial context (topography, drainage). Single-timestep only."

---

## 6:30–7:30 — RAG & Copilot (Honest)

**Speaker:**
"**RAG Knowledge Base:**
- FAISS IndexFlatIP (384-dim embeddings via all-MiniLM-L6-v2)
- 15 documents → ~30 chunks (tiny demo corpus)
- Starts **empty** — must be populated on first run
- Retrieval <3ms on this small index
- **`generate_answer()` returns template strings, not LLM answers**

**Climate Copilot:**
- 4-stage pipeline: Intent → Plan → Execute → Generate
- Intent classification: keyword-based (not LLM)
- 6 tools that call real backend APIs (forecast, risk, scenario, etc.)
- **Response generation: template strings only**
- Qwen3:8b declared in docker-compose but **never wired**

**The architecture is designed for LLM integration. The pipeline stages are implemented. What's missing is connecting the generator stage to an actual LLM call.** "

---

## 7:30–8:30 — Dashboard

**Speaker:**
"The Streamlit dashboard has 10 pages — 7 live, 3 mock:

**Live pages:** Home (overview map), Forecast (7-day predictions), Twin State, Scenario Simulator, Climate Risk, Maps, About

**Mock pages (placeholders):** Knowledge Base (08), Feedback (09), BHAI State (10)

The live pages render real-time charts from synthetic API data using Plotly and Folium. The mock pages show hardcoded placeholder content with no backend connectivity."

---

## 8:30–9:00 — Testing & Validation (Honest)

**Speaker:**
"**Test Suite:**
- **109 tests passing** (dashboard-focused)
- **18 known environment-related failures** (NumPy/FAISS/Streamlit version mismatches)
- **0% coverage** for models, API, RAG, and Copilot code

The previous '656 tests' claim was from a different codebase context and was published without verification. The actual test suite covers the dashboard adequately but leaves production code untested."

---

## 9:00–9:30 — Deployment

**Speaker:**
"**Docker Compose:** 8 services + 1 Ollama dependency

**Services:** nginx gateway, forecast API, twin API, scenario engine, risk API, RAG API, copilot, dashboard.

**CI/CD:** Minimal GitHub Actions — runs pytest on push only.

**Limitations:**
- No authentication — all endpoints open
- HTTP only — no TLS
- Docker images ~1GB+ each (full Python + PyTorch)
- Streamlit hot-reload broken in containers
- Ollama requires manual 8GB model pull

This is a **local demo deployment only.** Not production-ready."

---

## 9:30–10:00 — Impact, Roadmap & Closing

**Speaker:**
"**What's real:**
- Containerized 8-service deployment
- Synthetic pipeline end-to-end
- Digital twin with append-only versioning
- Scenario engine with 11 presets
- Risk scoring with configurable weights
- Dashboard with interactive charts

**What's next:**
1. **Real data** — connect NASA POWER / IMD / ISRO APIs (highest priority)
2. **Real LLM** — wire Qwen3:8b to copilot generator
3. **Real SHAP** — connect to model gradients
4. **Authentication** — API keys and HTTPS
5. **Test coverage** — models, APIs, RAG, copilot
6. **Scale** — Karnataka to all India

This is a **proof-of-concept** built in 6 weeks for this hackathon. The architecture works. The pipeline runs. The foundation is ready for the next team to take it to production.

Thank you. Happy to answer questions."
