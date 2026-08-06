# Climate Digital Twin — System Capabilities Matrix

## 1. Dashboard View Features (`dashboard/page_views/`)

| View Module | File Name | Primary Features |
|---|---|---|
| **Climate Overview** | `01_climate_overview.py` | Summary metrics, active location selection, historical temperature/rainfall trends |
| **Forecast Viewer** | `02_forecast_viewer.py` | Multi-model forecast charts (1, 3, 7-day), model comparison selector |
| **Digital Twin State** | `03_twin_state.py` | Versioned twin state metrics, state lineage table, observation update interface |
| **Scenario Simulator** | `04_scenario_simulator.py` | Interactive sliders for temperature offsets & rainfall multipliers, Monte Carlo fan charts |
| **Climate Risk** | `05_climate_risk.py` | Heat, flood, drought, composite risk gauges, SHAP waterfall explanation charts |
| **Reports & Insights** | `06_reports.py` | Automated report generation, summary export, PDF/Markdown download |
| **AI Copilot Chat** | `07_copilot_chat.py` | Conversational interface, session history, tool execution feedback |
| **Spatial Grid** | `08_spatial_grid.py` | Interactive Folium map, spatial grid cell overlays, spatial interpolation views |
| **Knowledge Base** | `08_knowledge_base.py` | Document collection browser, semantic search sandbox, index statistics |
| **Feedback** | `09_feedback.py` | User feedback submission, accuracy rating, comment logging |

---

## 2. API Endpoint Capability Matrix

| Path | Method | Purpose |
|---|---|---|
| `/health` | GET | Basic liveness probe |
| `/health/ready` | GET | Readiness probe checking all backend microservices |
| `/twin/state` | GET | Fetch active twin state for location |
| `/twin/state/history` | GET | Retrieve full version history of twin state |
| `/twin/state` | POST | Push new physical observation into twin state |
| `/forecast/predict` | GET | Run multi-horizon forecast inference |
| `/scenario/simulate` | POST | Execute what-if climate scenario simulation |
| `/scenario/compare` | GET | Compare multiple simulation results |
| `/risk/assess` | GET | Generate multi-hazard risk assessment & SHAP insights |
| `/rag/query` | POST | RAG search & document-grounded query answer |
| `/rag/search` | GET | Semantic/hybrid search over vector store |
| `/feedback` | POST | Submit feedback on predictions |
