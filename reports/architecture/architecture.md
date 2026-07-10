# Complete Architecture Report

## 1. System Architecture

The Climate Digital Twin is a 9-microservice system orchestrated via Docker Compose. All services run on a shared bridge network (`twin_network`) with health check dependencies ensuring correct startup order.

### Service Dependency Graph

```
streamlit-dashboard ──── fastapi-gateway ─────────────────────────────────┐
                              │                                            │
         ┌────────────────────┼────────────┬───────────┬──────────┬───────┤
         ▼                    ▼            ▼           ▼          ▼       ▼
   twin-state-mgr     forecast-engine  scenario-  risk-    rag-     copilot-
   (8001)             (8006)           engine    engine   service  agent
                                       (8002)    (8003)   (8004)   (8005)
                                                                     │
                                                               ollama:11434
```

## 2. Component Responsibilities

### 2.1 Twin State Manager (Port 8001)
- **Source:** `simulator/`
- **Config:** `simulator/configs/twin_config.yaml`
- **Key classes:**
  - `ClimateEntity` — Immutable dataclass with `update_state()`, geo-climate validation
  - `StateManager` — Append-only versioning with monotonically increasing IDs, rollback-as-new-version
  - `EventBus` — Pub/sub with 5 event types (ObservationIngested, StateUpdated, ForecastApplied, ScenarioApplied, Error)
  - `ParquetRepository` — Per-location file storage with snappy compression and in-memory cache
  - `DigitalTwinEngine` — Central orchestrator with repository rehydration on startup
- **Validation:** Karnataka bounds (11.5–18.5°N, 74.0–78.5°E), temperature (-10–55°C), rainfall (0–2000mm)
- **State types:** Current, Historical, Forecast, Scenario

### 2.2 Forecast Engine (Port 8006)
- **Source:** `models/`
- **Config:** `models/configs/model_config.yaml`
- **7 Model Architectures:**
  - `BaselineModel` — MLP feed-forward, hidden layers [64, 32], lr=0.001, epochs=50
  - `LSTMModel` — Stacked LSTM, hidden_dim=128, 2 layers, dropout=0.2, bidirectional, lr=0.001, epochs=100
  - `TransformerModel` — Encoder-only with sinusoidal positional encoding, d_model=128, nhead=4, 3 layers, lr=0.0005, epochs=100
  - `ITransformerModel` — Feature-axis Transformer with time projection, d_model=128, nhead=4, 3 layers
  - `PatchTSTModel` — Patch-embedded Transformer, patch_len=8, d_model=128, nhead=4, 3 layers
  - `TimeMixerModel` — MLP-mixer blocks with LayerNorm, d_model=128, 3 layers
  - `EnsembleMetaLearner` — Ridge regression meta-learner over base model predictions
- **Data:** Sequence length 30, batch size 64, 12 feature columns, 3 target columns
- **Training:** Adam optimizer, MSE loss, ReduceLROnPlateau, early stopping (patience 10)
- **Metrics:** RMSE, MAE, R², sMAPE
- **Safety:** `PhysicsValidator` — clamps rainfall ≥0 and ≤500mm, ensures Tmin ≤ Tmax, clips temps to ±55°C
- **Export:** TorchScript format

### 2.3 Scenario Engine (Port 8002)
- **Source:** `simulator/engine/scenario_engine.py`, `services/scenario_service.py`
- **Config:** `simulator/configs/scenario.yaml`
- **Key classes:**
  - `ScenarioDefinition` — Immutable params with 5 scenario types
  - `ScenarioValidator` — Input validation against YAML-configured bounds
  - `ScenarioBuilder` — Auto-ID generation, 11 presets
  - `ScenarioEngine` — Deterministic simulation (<3s), _apply_modifications per type, _compute_deltas
  - `ScenarioService` — Full lifecycle integration with DigitalTwinEngine
- **Scenario types:** Temperature (±0.5–5°C steps), Rainfall (±5–500% changes), Monsoon (delay/advance), Extreme Events (flood/heatwave/drought), Combined
- **Presets:** 11 (temp +1/+2/+3, temp -1/-2, rain +10/+25/+40, rain -10/-25/-40, monsoon delayed, monsoon early, heatwave, flood, drought)
- **Output formats:** JSON, CSV, Markdown

### 2.4 Risk Engine (Port 8003)
- **Source:** `risk/`
- **Config:** `risk/configs/risk.yaml`
- **Key classes:**
  - `HeatRiskScorer` — 0-100 score from max temp (40%), consecutive hot days (35%), seasonal anomaly (25%)
  - `FloodRiskScorer` — 0-100 score from rainfall intensity (40%), multi-day accumulation (35%), forecast uncertainty (25%)
  - `DroughtRiskScorer` — 0-100 score from rainfall deficit (40%), temperature increase (30%), dry period days (30%)
  - `CompositeRiskScorer` — Weighted: heat 0.33, flood 0.33, drought 0.34
  - `RiskEngine` — Orchestrator with `assess_all()` for complete assessment
- **Risk categories:** Very Low (0-20), Low (21-40), Moderate (41-60), High (61-80), Severe (81-100)
- **Explainability:** `SHAPExplainer` — deterministic synthetic estimation with feature attribution, global feature importance
- **Insights:** `InsightsEngine` — natural-language ClimateInsight objects per risk type
- **Output:** JSON + Markdown reports

### 2.5 RAG Service (Port 8004)
- **Source:** `knowledge/`
- **Config:** `knowledge/configs/rag.yaml`
- **Key classes:**
  - `DocumentLoader` (base) + 5 format implementations (MD, TXT, CSV, JSON, PDF stub)
  - `LoaderFactory` — Extension-based dispatch
  - `TextChunker` — Recursive paragraph→sentence→word splitting at 700 chars with 120 overlap
  - `EmbeddingModel` — sentence-transformers (all-MiniLM-L6-v2, 384-dim) with deterministic dummy fallback
  - `FAISSStore` — IndexFlatIP with L2 normalization, pickle metadata
  - `SemanticSearch` — Top-k=5, score threshold 0.5, metadata filtering
  - `ContextBuilder` — Numbered source lists, sectioned context, dashboard format
  - `IndexingPipeline` — load→chunk→embed→store pipeline
  - `KnowledgeAPI` — index/search/delete/list/rebuild/retrieve_context
- **Documents:** 5 indexed (karnataka_climate_profile.md, imd_weather_data.md, insat_satellite_products.md, climate_forecasting_methods.md, climate_risk_assessment.md)

### 2.6 Copilot Agent (Port 8005)
- **Source:** `copilot/`
- **Config:** `copilot/configs/copilot.yaml`
- **LLM:** Qwen3:8b via Ollama (temperature 0.1, max_tokens 1024, context 8192)
- **Multi-agent pipeline:**
  1. `IntentAgent` — Keyword-pattern matching, 8 intent types, sub-intent detection
  2. `PlanningAgent` — 8 intent-specific planners (forecast/twin/scenario/risk/rag/report/greeting/unknown)
  3. `Executor` — Per-step tool validation, perf_counter timing, error isolation
  4. `ResponseGenerator` — 7 intent-specific formatters with citations
  5. `Orchestrator` — End-to-end process() pipeline with memory integration
- **6 Tools:** forecast_tool, twin_tool, scenario_tool, risk_tool, rag_tool, report_tool
- **Memory:** Conversation buffer window (10 turns, 60min expiry)
- **Performance targets:** simple_query 2s, forecast 5s, simulation 8s, report 10s

### 2.7 API Gateway (Port 8000)
- **Source:** `backend/api/main.py`
- **Role:** Routes requests to downstream services
- **Health endpoint:** `GET /health`

### 2.8 Streamlit Dashboard (Port 8501)
- **Source:** `dashboard/`
- **Config:** `dashboard/config/config.py`
- **7 pages:**
  1. `01_climate_overview` — Interactive Folium map, current conditions, 90-day history
  2. `02_forecast_viewer` — Forecast map, confidence bands, day-by-day list, CSV download
  3. `03_twin_state` — Current state map, historical chart, forecast grid, version timeline
  4. `04_scenario_simulator` — Scenario presets, custom params, before/after + delta maps
  5. `05_climate_risk` — Risk heatmap, district ranking, composite gauge, SHAP waterfall
  6. `06_reports` — District summaries, data explorer, download, markdown reports
  7. `07_copilot_chat` — AI Copilot conversation interface
- **Components:** Cards, Sidebar, Filters (reusable)
- **Charts:** Time series, Comparison, Distribution, Risk Trends (Plotly)
- **Maps:** Climate overlay, Comparison, Risk heatmap (Folium + plugins)
- **API Client:** Synthetic data fallback for all 5 backend endpoints

### 2.9 Ollama (Port 11434)
- **Image:** `ollama/ollama:latest`
- **Model:** Qwen3:8b
- **Volume:** `ollama_data` for model persistence

## 3. Monitoring

### Prometheus (Port 9090)
- Scrape interval: 15s
- Targets: All 7 API services (twin-state-mgr, scenario-engine, risk-engine, rag-service, copilot-agent, forecast-engine, api-gateway)

### Grafana (Port 3000)
- Provisioned dashboard: `service-health.json` with 6 panels
- Data source: Prometheus

## 4. CI/CD Pipeline

### CI (GitHub Actions)
- **Triggers:** Push/PR to main/master
- **Jobs:** lint (ruff) → test (matrix 3.10/3.12) → docker (build all 7 images)

### CD (GitHub Actions)
- **Triggers:** Version tags (v*)
- **Steps:** Docker login → build all images → push to registry

## 5. Deployment Configuration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 11 services (8 app + 2 monitoring + Ollama) |
| `.env.example` | 14 environment variables |
| `nginx.conf` | Reverse proxy routing |
| `Dockerfile.*` | 8 service-specific Dockerfiles |
| `deployment/scripts/startup.sh` | One-click build+start |
| `deployment/scripts/shutdown.sh` | Graceful stop |
| `deployment/scripts/demo.sh` | 6-step demo walkthrough |
| `deployment/health/health_check.py` | Python health check utility |
| `deployment/cd/deploy.sh` | CD deployment script |

## 6. Data Configuration

| Config File | Settings |
|-------------|----------|
| `config/data_config.yaml` | Data sources, pipeline splits, Karnataka bounds, NASA POWER params |
| `models/configs/model_config.yaml` | All 7 model hyperparameters, training, evaluation, export |
| `simulator/configs/twin_config.yaml` | Grid resolution, storage engine, state limits, temperature/rainfall validation bounds |
| `simulator/configs/scenario.yaml` | Scenario bounds, validation rules, simulation constraints, output formats |
| `risk/configs/risk.yaml` | Risk category thresholds, per-risk weights, SHAP settings, output config |
| `knowledge/configs/rag.yaml` | Chunk size/overlap, embedding model, retrieval params, vector store path |
| `copilot/configs/copilot.yaml` | LLM model/host/params, memory config, enabled tools, prompt paths, performance targets |
