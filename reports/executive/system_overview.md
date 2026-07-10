# System Overview

## Data Flow (8-Step Pipeline)

```
  Dataset → Forecast → Digital Twin → Scenario → Risk → RAG → Copilot → Dashboard → Reports
```

### Step 1: Dataset
- **Source:** NASA POWER API (PRECTOTCORR, T2M_MAX, T2M_MIN) with synthetic fallback
- **Pipeline:** `pipeline/download.py` → `validate.py` → `clean.py` → `features.py` → `export.py`
- **Temporal split:** 70/15/15 chronological (train/val/test)
- **Feature engineering:** 12 features (DayOfYear, Month, Week, Season, Monsoon, RollingRain7/30, RollingTemp7/30, TempDiff, RainfallTrend, PriorRain7/30)
- **Grid resolution:** 0.25° rainfall, 1.0° temperature
- **Date range:** 1981-01-01 to 2023-12-31

### Step 2: Forecast
- **Engine:** `models/` — 7 architectures (Baseline MLP, LSTM, Transformer, iTransformer, PatchTST, TimeMixer, Ensemble)
- **Horizons:** 1-day, 3-day, 7-day predictions
- **Output:** Rainfall, MaxTemp, MinTemp with 95% confidence intervals
- **Safety:** PhysicsValidator layer clamps rainfall ≥0, ensures Tmin ≤ Tmax

### Step 3: Digital Twin
- **Engine:** `simulator/engine/twin_engine.py` — DigitalTwinEngine
- **State management:** Immutable append-only versioning, per-location version history
- **Storage:** Parquet repository with snappy compression
- **Events:** Pub/sub EventBus with 5 event types

### Step 4: Scenario
- **Engine:** `simulator/engine/scenario_engine.py` — ScenarioEngine
- **Types:** Temperature (±1–3°C), Rainfall (±10–40%), Monsoon (delay/advance/intensity), Extreme Events (flood/heatwave/drought), Combined
- **Presets:** 11 predefined scenarios
- **Validity:** Deterministic execution <3s, enforced ≥0 rainfall

### Step 5: Risk
- **Engine:** `risk/engine/risk_engine.py` — RiskEngine
- **Scoring:** Heat (0–100), Flood (0–100), Drought (0–100), Composite (weighted)
- **Categories:** Very Low (0–20), Low (21–40), Moderate (41–60), High (61–80), Severe (81–100)
- **Explainability:** Deterministic SHAP estimation with feature attribution

### Step 6: RAG
- **Engine:** `knowledge/` — FAISS + sentence-transformers
- **Documents:** 5 indexed documents (ISRO, IMD, Government, Research, Risk)
- **Chunking:** Recursive paragraph→sentence→word at 700 chars with 120 overlap
- **Search:** Top-k=5 with score threshold (0.5) and metadata filtering

### Step 7: Copilot
- **Engine:** `copilot/` — Multi-agent orchestration
- **Pipeline:** Intent Classification → Planning → Execution → Response Generation
- **Tools:** 6 registered (forecast, twin, scenario, risk, RAG, report)
- **LLM:** Qwen3:8b via Ollama (temperature 0.1, context 8192)
- **Memory:** Conversation buffer window (10 turns, 60min expiry)

### Step 8: Dashboard & Reports
- **Dashboard:** 7-page Streamlit app (Overview, Forecast, Twin State, Scenario, Risk, Reports, Copilot)
- **Reports:** JSON + Markdown from risk engine, scenario engine, conversation history
- **Maps:** Folium with climate overlays, district boundaries, risk heatmaps
- **Charts:** Plotly (time series, comparison, distribution, risk trends)

## Microservice Architecture

```
                        ┌──────────────────┐
                        │  Streamlit Dash  │
                        │    Port 8501     │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   API Gateway    │
                        │    Port 8000     │
                        └──┬──┬──┬──┬──┬──┘
                           │  │  │  │  │
      ┌─────┐ ┌────┐ ┌────┐│ ┌──┴┐ ┌──┴┐ ┌──────────┐
      │Twin │ │Fore│ │Scen││ │Rsk│ │RAG│ │ Copilot  │
      │Core │ │cast│ │Eng ││ │Eng│ │Svc│ │ Agent    │
      │8001 │ │8006│ │8002││ │800│ │800│ │ 8005     │
      └─────┘ └────┘ └────┘│ └───┘ └───┘ └──────────┘
                           │
                     ┌─────▼──────┐
                     │   Ollama   │
                     │  11434     │
                     └────────────┘
```

## Service Port Mapping

| Service | Port | Protocol | Health Endpoint |
|---------|------|----------|-----------------|
| fastapi-gateway | 8000 | HTTP | `GET /health` |
| twin-state-mgr | 8001 | HTTP | `GET /health` |
| scenario-engine | 8002 | HTTP | `GET /health` |
| risk-engine | 8003 | HTTP | `GET /health` |
| rag-service | 8004 | HTTP | `GET /health` |
| copilot-agent | 8005 | HTTP | `GET /health` |
| forecast-engine | 8006 | HTTP | `GET /health` |
| streamlit-dashboard | 8501 | HTTP | — |
| ollama | 11434 | HTTP | `ollama list` |
| prometheus | 9090 | HTTP | — |
| grafana | 3000 | HTTP | — |

## Pilot Scope

| Dimension | Detail |
|-----------|--------|
| **Region** | Karnataka, India |
| **Bounds** | 11.5–18.5°N, 74.0–78.5°E |
| **Grid** | 0.25° resolution |
| **Districts** | Bengaluru Urban, Mysuru, Belagavi, Dakshina Kannada, Kalaburagi |
| **Variables** | Rainfall (mm), MaxTemp (°C), MinTemp (°C) |
| **Horizons** | 1-day, 3-day, 7-day |
| **Data Period** | 1981–2023 (43 years) |

## Key Constraints

| Constraint | Specification |
|-----------|--------------|
| Temperature bounds | -10°C to 55°C (physics validation) |
| Rainfall bounds | 0–500 mm/day (physics validation) |
| Scenario execution | <3000ms |
| Deterministic | Same inputs always produce same outputs |
| Offline mode | Full synthetic data fallback without external APIs |
| Python | >=3.10 required |
| Docker | All services containerized |
