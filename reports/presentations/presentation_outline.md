# Presentation Outline — 20 Slides
## AI-Powered Digital Twin of India's Climate
### ISRO BAH 2026 — Challenge 5

---

## Section 1: Problem & Motivation (Slides 1–3)

### Slide 1: Title Slide
- Project: AI-Powered Digital Twin of India's Climate
- ISRO BAH 2026 — Challenge 5
- Team / Project name
- Date: June 2026
- Tagline: *From Data to Decisions: A Digital Twin for Climate Resilience*

### Slide 2: The Climate Challenge
- India: 3-5% GDP lost annually to climate disasters
- 60% agriculture dependent on monsoon
- Problem: Data exists but is fragmented, not localized, not actionable
- Pilot focus: Karnataka — 5 districts across diverse climate zones
- Key question: Can we unify forecasting, simulation, risk, and AI into one system?

### Slide 3: Solution Overview
- AI-powered Digital Twin of India's Climate
- 9 microservices, 8-step data pipeline
- 7 model architectures for forecasting
- RAG knowledge base + AI Copilot for natural language interaction
- Full Docker Compose deployment with monitoring

---

## Section 2: Architecture & Design (Slides 4–6)

### Slide 4: System Architecture Diagram
- 9 microservice architecture
- Docker Compose orchestration
- Service topology: Gateway -> 6 backend services + Dashboard + Ollama
- Monitoring: Prometheus + Grafana
- Key: All services containerized with health checks

### Slide 5: Data Flow Pipeline
- 8-step pipeline: Dataset -> Forecast -> Digital Twin -> Scenario -> Risk -> RAG -> Copilot -> Dashboard
- Each step with source file and service port
- Visual: sequence diagram from system_overview.md
- Data flows through with deterministic synthetic fallback

### Slide 6: Tech Stack
- ML Framework: PyTorch 2.0+
- Backend: FastAPI + Uvicorn
- Dashboard: Streamlit + Plotly + Folium
- Vector Store: FAISS (IndexFlatIP)
- Embeddings: sentence-transformers (all-MiniLM-L6-v2)
- LLM: Qwen3:8b via Ollama
- Explainability: SHAP (deterministic offline)
- Storage: Parquet + DuckDB
- Monitoring: Prometheus + Grafana

---

## Section 3: Data Pipeline & Models (Slides 7–9)

### Slide 7: Data Pipeline
- Source: NASA POWER API (1981-2023, 43 years)
- Coverage: Karnataka, 48 grid cells, 0.25°-1.0° resolution
- Pipeline: Download -> Validate -> Clean -> Feature Engineering -> Export
- 12 engineered features: temporal, rolling, trend, prior rainfall
- Output: 628,200 processed rows, 70/15/15 temporal split
- Quality: 0 missing values, bounds validated

### Slide 8: Forecasting Models
- 7 model architectures
- Three trained: Baseline MLP (RMSE 4.59), LSTM (RMSE 4.53 best), Transformer (RMSE 4.57)
- Three stubs: PatchTST, TimeMixer, iTransformer
- Ensemble: Ridge regression meta-learner
- All models achieve R² = 0.87
- PhysicsValidator safety layer: rainfall >= 0, Tmin <= Tmax, temp bounds

### Slide 9: Training & Evaluation
- Sliding window of 30 days, batch size 64
- Adam optimizer, MSE loss, ReduceLROnPlateau scheduler
- Early stopping (patience 10)
- Metrics: RMSE, MAE, R², sMAPE
- 95% confidence intervals on predictions
- Model registry with metadata.json

---

## Section 4: Digital Twin & Scenarios (Slides 10–12)

### Slide 10: Digital Twin Core
- Immutable ClimateEntity dataclass with geo-climate validation
- StateManager: Append-only versioning, monotonically increasing version IDs
- Rollback creates new version (no history destruction)
- EventBus: Pub/sub with 5 event types
- ParquetRepository: Per-location storage with snappy compression
- 4 state types: Current, Historical, Forecast, Scenario

### Slide 11: Scenario Simulation Engine
- 5 scenario types: Temperature, Rainfall, Monsoon, Extreme Events, Combined
- 11 preset scenarios: +1/+2/+3°C, -1/-2°C, +10/+25/+40% rain, -10/-25/-40% rain
- Deterministic execution guaranteed < 3 seconds
- Physics constraints: rainfall >= 0 enforced
- Output formats: JSON, CSV, Markdown
- Integration with digital twin for baseline state

### Slide 12: Scenario Examples & Visuals
- Before/after comparison maps
- Delta charts per location
- Example: +2°C temperature scenario across Karnataka districts
- Example: -25% rainfall scenario impact on agriculture

---

## Section 5: Risk & Explainability (Slides 13–14)

### Slide 13: Climate Risk Engine
- Four scoring modules:
  - Heat Risk (0-100): max temp 40%, hot days 35%, anomaly 25%
  - Flood Risk (0-100): intensity 40%, accumulation 35%, uncertainty 25%
  - Drought Risk (0-100): deficit 40%, temp increase 30%, dry period 30%
  - Composite: weighted (heat 0.33, flood 0.33, drought 0.34)
- 5 categories: Very Low (0-20) to Severe (81-100)
- Configurable weights from risk.yaml

### Slide 14: SHAP Explainability
- Deterministic synthetic SHAP estimation
- Per-feature contribution values for each risk score
- Global feature importance rankings
- Natural-language insights engine
- Example: "Consecutive hot days are the primary driver of high heat risk in Kalaburagi"
- Outputs: JSON and Markdown reports

---

## Section 6: RAG & Copilot (Slides 15–16)

### Slide 15: RAG Knowledge Base
- FAISS IndexFlatIP vector store (384-dim)
- 15 documents indexed, 30 chunks
- 5 categories: Government, ISRO, IMD, Research, Risk
- Recursive chunking at 700/120 characters
- Retrieval: top-k=5, threshold 0.5, latency < 3ms
- Benchmark: 100% retrieval rate, mean score 0.659
- 5 format loaders: MD, TXT, CSV, JSON, PDF (stub)

### Slide 16: AI Climate Copilot
- 4-step pipeline: Intent -> Plan -> Execute -> Generate
- 8 intent types, 6 tools, keyword classification
- LLM: Qwen3:8b via Ollama (temp 0.1)
- Conversation memory: 10 turns, 60min expiry
- Performance: simple < 50ms, forecast < 100ms
- API: /ask, /conversation, /health

---

## Section 7: Results & Validation (Slides 17–18)

### Slide 17: Performance Metrics
- 656 total tests, 57 test files
- 17/17 E2E pipeline stages (100%)
- Best RMSE: 4.53 (LSTM), R²: 0.87
- Inference: Transformer 26.8ms total (fastest trained)
- RAG latency: < 3ms, Copilot simple: < 50ms
- Codebase: 262 Python files, 17,354 LOC

### Slide 18: Benchmark Comparison
- LSTM vs Transformer vs Baseline comparison table
- RMSE bar chart, inference time chart
- Checkpoint size comparison (94 KB to 2,847 KB)
- RAG retrieval scores by category
- All trained models at R² = 0.87

---

## Section 8: Future & Impact (Slides 19–20)

### Slide 19: Societal Impact
- Farmers: 7-day forecasts for sowing and irrigation planning
- Disaster management: district-level risk scores for preparedness
- Policy: what-if scenario analysis for climate adaptation
- Democracy of data: AI Copilot makes climate intelligence accessible
- Open source: any state or district can adapt and deploy

### Slide 20: Future Roadmap
- **National scale:** Karnataka -> All Indian states
- **Advanced models:** Train PatchTST, TimeMixer, iTransformer
- **Real SHAP:** Connect to model gradients
- **Live data:** Real-time IMD/INSAT integration
- **Mobile app:** Farmer-facing notifications
- **Uncertainty:** Conformal prediction intervals
- **Decision Intelligence:** Irrigation recommendations, anomaly detection
- **V2 Architecture:** Already designed — 11 services with data fusion, uncertainty, decision intelligence

---

## Appendix: Backup Slides

### A1: Detailed Model Architectures
### A2: API Endpoint Reference
### A3: Configuration YAML Reference
### A4: Docker Compose Service Definitions
### A5: E2E Test Methodology
### A6: Lessons Learned from Development
