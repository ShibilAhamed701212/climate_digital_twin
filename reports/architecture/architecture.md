# Architecture Report

> **Hackathon Proof-of-Concept** — Synthetic data throughout. Not production-ready.

---

## 8-Service Architecture

The system runs 8 Docker services plus an external Ollama dependency:

| # | Service | Port | Purpose | Status |
|---|---------|------|---------|--------|
| 1 | Gateway | 80 | nginx reverse proxy | ✅ Routes to all services |
| 2 | Forecasting API | 8005 | ML model inference | ✅ 3 trained models on synthetic data |
| 3 | Twin API | 8002 | Climate state management | ✅ Synthetic state versioning |
| 4 | Scenario Engine | 8003 | Climate perturbation simulation | ✅ <3s deterministic |
| 5 | Risk API | 8004 | Hazard scoring | ✅ 4 modules on synthetic data |
| 6 | RAG API | 8006 | Vector retrieval | ⚠️ FAISS empty by default |
| 7 | Copilot API | 8007 | AI assistant | ⚠️ Mock responses only |
| 8 | Dashboard | 8501 | Streamlit UI | ✅ 7 live + 3 mock pages |
| — | Ollama (dep) | 11434 | LLM runtime | ⚠️ Not wired to copilot |

---

## Data Flow (All Synthetic)

```
Synthetic Data Generator
        │
        ▼
  Forecasting API ───→ Model Checkpoints (3 trained)
        │
        ▼
  Digital Twin ───→ StateManager (append-only versions)
        │
        ▼
  Scenario Engine ───→ 11 presets, deterministic deltas
        │
        ▼
  Risk API ───→ Heat/Flood/Drought/Composite scores
        │
        ▼
  RAG API ───→ FAISS index (POPULATED FIRST RUN)
        │
        ▼
  Copilot API ───→ Keyword → Mock Response
        │
        ▼
  Dashboard (Streamlit) ← 7 live pages + 3 mock pages
```

---

## Component Responsibilities

### Forecasting API (port 8005)
- **Models:** MLP, LSTM, Transformer (trained on synthetic data)
- **Stubs:** PatchTST, TimeMixer, iTransformer (class definitions only)
- **Ensemble:** Ridge regression wrapper
- **Validation:** PhysicsValidator (rainfall >= 0, Tmin <= Tmax)
- **Endpoints:** `/predict`, `/models`, `/health`

### Digital Twin (port 8002)
- **Entity:** `ClimateEntity` immutable dataclass with geo-climate validation
- **StateManager:** Append-only, monotonically increasing version IDs
- **EventBus:** Pub/sub with 5 event types
- **Repository:** Parquet per-location with snappy compression
- **States:** Current, Historical, Forecast, Scenario

### Scenario Engine (port 8003)
- 5 types: Temperature, Rainfall, Monsoon, Extreme Events, Combined
- 11 presets: +1/+2/+3°C, -1/-2°C, +10/+25/+40% rain, -10/-25/-40% rain
- Physics constraints enforced (rainfall >= 0)
- Deterministic < 3 seconds

### Risk API (port 8004)
- Heat Risk: max temp 40%, hot days 35%, anomaly 25%
- Flood Risk: intensity 40%, accumulation 35%, uncertainty 25%
- Drought Risk: deficit 40%, temp increase 30%, dry period 30%
- Composite: weighted (heat 0.33, flood 0.33, drought 0.34)
- All configurable from `risk.yaml`

### RAG API (port 8006)
- FAISS IndexFlatIP, 384-dim
- **15 documents, ~30 chunks** (small demo corpus)
- Top-k=5, threshold 0.5
- 5 format loaders: MD, TXT, CSV, JSON, PDF (stub)
- `generate_answer()` is a mock

### Copilot API (port 8007)
- 4-stage pipeline: Intent → Plan → Execute → Generate
- 8 intent types via keyword classification
- 6 tools (get_forecast, get_risk, etc.)
- Conversation memory: 10 turns, 60min expiry
- **All responses are template-based (mock)**

### Dashboard (port 8501)
- 7 live pages: Home, Forecast, Twin, Risk, Scenario, About, Maps
- 3 mock pages: Knowledge Base (08), Feedback (09), BHAI State (10)
- Charts: Plotly time series + Folium maps
- All data from synthetic API calls

---

## Configuration

Centralized in `config/`:
- `config.yaml` — 15 sample Karnataka districts
- `risk.yaml` — Risk scoring weights
- `scenarios.yaml` — Scenario definitions
- `model_config.yaml` — Model hyperparameters
- Dashboard config in `app/config.py`

---

## CI/CD

GitHub Actions workflow exists but is minimal. Runs pytest on push. No linting, type checking, or deployment pipeline.
