# Architecture Migration Plan: Phase 0

## Freeze Declaration

**Date:** July 1, 2026
**Canonical Repository:** `D:\var-codes\climate-digital-twin` (266 Python files, ~21K LOC)
**Source Repository:** `D:\var-codes\BHAI` (464 Python files, ~67K LOC)
**Verdict:** ~0% code identity, ~25% architectural similarity — **different projects with similar goals**

> **Rule:** `climate-digital-twin` provides the architecture (folder structure, Docker layout, microservice grid,
> service URLs, naming conventions). `BHAI` provides superior implementations where identified. Never replace
> architecture with BHAI — only import code that fits the canonical architecture.

---

## 1. Executive Summary

This document is the sole source of truth for the BHAI → climate-digital-twin migration. Every module in both
repositories is assigned one of five decisions, and every phase of work is specified with dependencies,
risks, and acceptance criteria. No code changes happen until Phase A begins.

### Decision Categories

| Decision | Meaning | Count |
|----------|---------|-------|
| **KEEP ORIGINAL** | The canonical implementation is superior; leave unchanged | 2 |
| **KEEP BHAI** | BHAI implementation is entirely new or clearly better; import as-is | 2 |
| **MERGE** | Both have strengths; combine into canonical | 9 |
| **REPLACE** | BHAI implementation completely supersedes canonical | 1 |
| **ARCHIVE** | Neither is needed; preserve for reference only | 0 |

---

## 2. Complete Migration Matrix

Every module in both repositories, mapped to its decision and destination.

### 2.1 API Gateway

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `backend/api/main.py` | `api_gateway/main.py` | **REPLACE** | `backend/api/main.py` | Original is a skeleton with only `/health`. BHAI has 7 route modules, 4 middleware, 40+ models, DI pattern. |
| `backend/api/routes/__init__.py` (empty) | `api_gateway/routes/health.py` | **REPLACE** | `backend/api/routes/` | Replace empty stubs with BHAI's complete route modules (adapted to canonical URLs). |
| `backend/api/models/__init__.py` (empty) | `api_gateway/models.py` | **REPLACE** | `backend/api/models.py` | BHAI's models.py (549 LOC, 40+ models) replaces empty stub. |
| `backend/api/services/__init__.py` (empty) | `api_gateway/dependencies.py` | **REPLACE** | `backend/api/dependencies.py` | BHAI's singleton DI pattern replaces empty stub. |
| `backend/core/__init__.py` (empty) | `api_gateway/config.py` | **REPLACE** | `backend/core/config.py` | BHAI's GatewayConfig dataclass replaces empty stub. |
| — | `api_gateway/middleware.py` | **KEEP BHAI** | `backend/api/middleware.py` | New: CORS, timing, error logging, API key auth. |
| — | `api_gateway/routes/feedback.py` | **KEEP BHAI** | `backend/api/routes/feedback.py` | New: feedback submission and analytics. |

### 2.2 Digital Twin Core

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `simulator/engine/twin_engine.py` | `climatedt/twin/state_manager.py` | **MERGE** | `simulator/engine/twin_engine.py` | Keep original's orchestrator pattern. Import BHAI's enriched state management patterns. |
| `simulator/state_manager/manager.py` | `climatedt/twin/state_manager.py` | **MERGE** | `simulator/state_manager/manager.py` | Keep original immutable version chain. Add BHAI's rollback and query improvements. |
| `simulator/state_manager/version.py` | _implicit_ | **KEEP ORIGINAL** | `simulator/state_manager/version.py` | Original Version dataclass is correct. |
| `simulator/repository/parquet_repository.py` | `climatedt/storage/versioned_state_store.py` | **MERGE** | `simulator/repository/parquet_repository.py` | Keep original ABC + Parquet. Add BHAI's append-only versioning. |
| — | `climatedt/storage/feature_store.py` | **KEEP BHAI** | `simulator/repository/feature_store.py` | New: feature store for ML features. |
| — | `climatedt/storage/dataset_registry.py` | **KEEP BHAI** | `simulator/repository/dataset_registry.py` | New: dataset versioning. |
| `simulator/events/event_bus.py` | `runtime/event_bus.py` | **KEEP ORIGINAL** | `simulator/events/event_bus.py` | Original synchronous pub/sub matches this project's needs better than runtime's generic version. |
| `simulator/entities/climate_entity.py` | `climatedt/models/twin_state.py` | **MERGE** | `simulator/entities/climate_entity.py` | Keep original ClimateEntity. Import BHAI's TwinState/TwinEntity fields and validation. |
| — | `climatedt/twin/graph.py` | **KEEP BHAI** | `simulator/twin/graph.py` | New: entity relationship graph. |
| — | `climatedt/twin/conflict_resolver.py` | **KEEP BHAI** | `simulator/twin/conflict_resolver.py` | New: conflict detection and resolution. |
| — | `climatedt/twin/reconciliation.py` | **KEEP BHAI** | `simulator/twin/reconciliation.py` | New: cross-source state reconciliation. |
| — | `climatedt/twin/anomaly.py` | **KEEP BHAI** | `simulator/twin/anomaly.py` | New: anomaly detection on twin state. |
| — | `climatedt/twin/synchronizer.py` | **KEEP BHAI** | `simulator/twin/synchronizer.py` | New: multi-source state synchronizer. |
| — | `climatedt/twin/historical.py` | **KEEP BHAI** | `simulator/twin/historical.py` | New: historical baseline computation. |
| `simulator/api/main.py` | `services/twin_service/main.py` | **KEEP ORIGINAL** | `simulator/api/main.py` | Original API endpoints are complete. BHAI's twin service is thinner (165 LOC). |

### 2.3 Scenario Engine

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `simulator/engine/scenario_engine.py` | `climatedt/scenario/generator.py` | **MERGE** | `simulator/engine/scenario_engine.py` | Keep original deterministic engine. Import BHAI's Monte Carlo, perturbation, ensemble. |
| `simulator/scenarios/scenario_builder.py` | `climatedt/scenario/generator.py` | **MERGE** | `simulator/scenarios/scenario_builder.py` | Keep 11 presets + add BHAI's 9 templates (including IPCC). |
| `simulator/services/scenario_service.py` | `climatedt/scenario/service.py` | **MERGE** | `simulator/services/scenario_service.py` | Merge orchestration logic. |
| `simulator/models/scenario_models.py` | _implicit_ | **KEEP ORIGINAL** | `simulator/models/scenario_models.py` | Original ScenarioDefinition/SimulationResult/ScenarioRun are sufficient. |
| `simulator/validators/scenario_validator.py` | _implicit_ | **KEEP ORIGINAL** | `simulator/validators/scenario_validator.py` | Original validation logic is complete. |
| `simulator/scenarios/api.py` | `services/scenario_service/main.py` | **KEEP ORIGINAL** | `simulator/scenarios/api.py` | Original API is complete with 6 endpoints. |
| — | `climatedt/scenario/perturbation.py` | **KEEP BHAI** | `simulator/scenarios/perturbation.py` | New: perturbation engine. |
| — | `climatedt/scenario/monte_carlo.py` | **KEEP BHAI** | `simulator/scenarios/monte_carlo.py` | New: Monte Carlo simulation. |
| — | `climatedt/scenario/ensemble.py` | **KEEP BHAI** | `simulator/scenarios/ensemble.py` | New: ensemble simulation. |
| — | `climatedt/scenario/comparison.py` | **KEEP BHAI** | `simulator/scenarios/comparison.py` | New: scenario comparison. |

### 2.4 Risk Engine

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `risk/engine/risk_engine.py` | `climatedt/risk/service.py` | **KEEP ORIGINAL** | `risk/engine/risk_engine.py` | Original is more complete (separate config loading, SHAP integration, report generation). |
| `risk/scoring/drought_risk.py` | `climatedt/risk/models/drought_risk.py` | **KEEP ORIGINAL** | `risk/scoring/drought_risk.py` | Original weights/thresholds are domain-tuned. |
| `risk/scoring/flood_risk.py` | `climatedt/risk/models/flood_risk.py` | **KEEP ORIGINAL** | `risk/scoring/flood_risk.py` | Original scoring logic is equivalent or better. |
| `risk/scoring/heat_risk.py` | `climatedt/risk/models/heat_risk.py` | **KEEP ORIGINAL** | `risk/scoring/heat_risk.py` | Original has better contribution breakdown. |
| `risk/scoring/composite_risk.py` | `climatedt/risk/models/composite_risk.py` | **KEEP ORIGINAL** | `risk/scoring/composite_risk.py` | Original weighted average is standard. |
| — | `climatedt/risk/models/agriculture_risk.py` | **KEEP BHAI** | `risk/scoring/agriculture_risk.py` | New: agriculture-specific risk model. |
| `risk/explainability/shap_explainer.py` | `climatedt/risk/explainability.py` | **KEEP ORIGINAL** | `risk/explainability/shap_explainer.py` | Original SHAP explainer is more detailed. |
| `risk/explainability/insights_engine.py` | _implicit_ | **KEEP ORIGINAL** | `risk/explainability/insights_engine.py` | Original natural language insights are unique. |
| `risk/reports/report_generator.py` | _implicit_ | **KEEP ORIGINAL** | `risk/reports/report_generator.py` | Original JSON/Markdown report generation. |
| `risk/models/risk_models.py` | _implicit_ | **KEEP ORIGINAL** | `risk/models/risk_models.py` | Original frozen dataclass models are well-designed. |
| `risk/api/main.py` | `services/risk_service/main.py` | **KEEP ORIGINAL** | `risk/api/main.py` | Original has more endpoints (assess/heat/flood/drought/composite/report). |

### 2.5 RAG / Knowledge Base

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `knowledge/embeddings/embedding_model.py` | `climatedt/rag/embeddings.py` | **MERGE** | `knowledge/embeddings/embedding_model.py` | Keep original structure. Import BHAI's multi-strategy fallback (TF-IDF, random). |
| `knowledge/vector_store/faiss_store.py` | `climatedt/rag/vector_store.py` | **MERGE** | `knowledge/vector_store/faiss_store.py` | Both use FAISS. Add BHAI's persistence and collection management. |
| `knowledge/retriever/semantic_search.py` | `climatedt/rag/retrieval.py` | **MERGE** | `knowledge/retriever/semantic_search.py` | Add BHAI's hybrid search (dense + BM25). |
| `knowledge/retriever/context_builder.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/retriever/context_builder.py` | Original LLM context builder with token-aware truncation. |
| `knowledge/loaders/base.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/base.py` | Original loader ABC is well-designed. |
| `knowledge/loaders/md_loader.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/md_loader.py` | Original markdown loader with title extraction. |
| `knowledge/loaders/txt_loader.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/txt_loader.py` | Original text loader. |
| `knowledge/loaders/csv_loader.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/csv_loader.py` | Original CSV loader with formatted output. |
| `knowledge/loaders/json_loader.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/json_loader.py` | Original JSON loader. |
| `knowledge/loaders/factory.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/loaders/factory.py` | Original loader factory. |
| `knowledge/chunkers/text_chunker.py` | _implicit_ | **KEEP ORIGINAL** | `knowledge/chunkers/text_chunker.py` | Original recursive chunker with overlap. |
| `knowledge/pipelines/indexing_pipeline.py` | `climatedt/rag/ingestion.py` | **MERGE** | `knowledge/pipelines/indexing_pipeline.py` | Merge both ingestion patterns. |
| `knowledge/api/main.py` | `services/rag_service/main.py` | **KEEP ORIGINAL** | `knowledge/api/main.py` | Original API endpoint. |
| `knowledge/api/search_api.py` | `climatedt/rag/service.py` | **MERGE** | `knowledge/api/search_api.py` | Merge BHAI's KnowledgeBase/collection management into original API. |

### 2.6 Copilot

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `copilot/workflows/orchestrator.py` | `copilot_agent/service.py` | **MERGE** | `copilot/workflows/orchestrator.py` | Keep original multi-agent pipeline. Import BHAI's cleaner intent→route flow. |
| `copilot/agent/intent_agent.py` | `copilot_agent/intent.py` | **MERGE** | `copilot/agent/intent_agent.py` | Keep original structure. Import BHAI's superior keyword scoring and tie-breaking. |
| `copilot/planner/planner.py` | `copilot_agent/router.py` | **MERGE** | `copilot/planner/planner.py` | Keep original plan structure. Import BHAI's service routing. |
| `copilot/workflows/executor.py` | _implicit (in service.py)_ | **KEEP ORIGINAL** | `copilot/workflows/executor.py` | Original executor with error handling. |
| `copilot/workflows/generator.py` | _implicit (in service.py)_ | **KEEP ORIGINAL** | `copilot/workflows/generator.py` | Original generator with LLM+fallback. |
| `copilot/llm/ollama_client.py` | `copilot_agent/ollama_client.py` | **MERGE** | `copilot/llm/ollama_client.py` | Import BHAI's improved streaming support and error handling. |
| `copilot/memory/conversation_memory.py` | `copilot_agent/session.py` | **KEEP ORIGINAL** | `copilot/memory/conversation_memory.py` | Original sliding-window memory is more feature-rich. |
| `copilot/tools/*.py` | _implicit_ | **KEEP ORIGINAL** | `copilot/tools/*.py` | Original 6-tool system with BaseTool ABC is well-designed. |
| `copilot/clients/*.py` | _implicit_ | **KEEP ORIGINAL** | `copilot/clients/*.py` | Original service client wrappers. |
| `copilot/api/main.py` | `copilot_agent/web.py` | **KEEP ORIGINAL** | `copilot/api/main.py` | Original API with health/ask/conversation endpoints. |
| `copilot/prompts/*.txt` | _implicit_ | **KEEP ORIGINAL** | `copilot/prompts/*.txt` | Original prompt templates. |

### 2.7 Dashboard

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `dashboard/app.py` | `dashboard/Home.py` | **KEEP ORIGINAL** | `dashboard/app.py` | Original has richer app entry point (CSS, sidebar, navigation). |
| `dashboard/pages/01_climate_overview.py` | — | **KEEP ORIGINAL** | `dashboard/pages/01_climate_overview.py` | Unique page with maps, metrics, trends. |
| `dashboard/pages/02_forecast_viewer.py` | `dashboard/pages/02_Forecast.py` | **MERGE** | `dashboard/pages/02_forecast_viewer.py` | Keep original layout/features. Import BHAI's cleaner data handling. |
| `dashboard/pages/03_twin_state.py` | `dashboard/pages/08_Twin_State.py` | **MERGE** | `dashboard/pages/03_twin_state.py` | Keep original 4-tab layout. Import BHAI's enriched twin state display. |
| `dashboard/pages/04_scenario_simulator.py` | `dashboard/pages/03_Scenario.py` | **KEEP ORIGINAL** | `dashboard/pages/04_scenario_simulator.py` | Original has richer UI (3 tabs, before/after maps, delta visualization). |
| `dashboard/pages/05_climate_risk.py` | `dashboard/pages/01_Risk_Assessment.py` | **KEEP ORIGINAL** | `dashboard/pages/05_climate_risk.py` | Original has superior 4-tab layout with SHAP, heatmap, gauges. |
| `dashboard/pages/06_reports.py` | `dashboard/pages/06_Reports.py` | **KEEP ORIGINAL** | `dashboard/pages/06_reports.py` | Original has richer 4-tab report system. |
| `dashboard/pages/07_copilot_chat.py` | `dashboard/pages/07_Copilot_Chat.py` | **MERGE** | `dashboard/pages/07_copilot_chat.py` | Import BHAI's improved chat UI components. |
| — | `dashboard/pages/05_Feedback.py` | **KEEP BHAI** | `dashboard/pages/08_feedback.py` | New: user feedback page. |
| — | `dashboard/pages/04_Knowledge_Base.py` | **KEEP BHAI** | `dashboard/pages/09_knowledge_base.py` | New: RAG knowledge exploration page. |
| `dashboard/charts/*.py` | _implicit_ | **KEEP ORIGINAL** | `dashboard/charts/*.py` | Original Plotly charts are richer and more varied. |
| `dashboard/components/*.py` | _implicit_ | **KEEP ORIGINAL** | `dashboard/components/*.py` | Original sidebar/filters/cards components. |
| `dashboard/maps/*.py` | _implicit_ | **KEEP ORIGINAL** | `dashboard/maps/*.py` | Original Folium maps with heatmap/comparison/delta. |
| `dashboard/services/api_client.py` | `dashboard/utils.py` | **MERGE** | `dashboard/services/api_client.py` | Keep original DashboardAPI class. Import BHAI's utils.py patterns for business logic extraction. |
| `dashboard/config/config.py` | `dashboard/config/config.py` | **MERGE** | `dashboard/config/config.py` | Merge configuration constants. |
| `dashboard/assets/style.css` | — | **KEEP ORIGINAL** | `dashboard/assets/style.css` | Original custom CSS is unique. |

### 2.8 ML Models

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `models/baseline/model.py` | `climatedt/ml/baselines.py` | **KEEP ORIGINAL** | `models/baseline/model.py` | Original MLP architecture is well-implemented. |
| `models/lstm/model.py` | `climatedt/ml/models/forecasting/lstm_model.py` | **MERGE** | `models/lstm/model.py` | Both implement LSTM. Merge best patterns from both. |
| `models/transformer/model.py` | — | **KEEP ORIGINAL** | `models/transformer/model.py` | No BHAI equivalent. Unique canonical asset. |
| `models/itransformer/model.py` | — | **KEEP ORIGINAL** | `models/itransformer/model.py` | No BHAI equivalent. Unique canonical asset. |
| `models/patchtst/model.py` | — | **KEEP ORIGINAL** | `models/patchtst/model.py` | No BHAI equivalent. Unique canonical asset. |
| `models/timemixer/model.py` | — | **KEEP ORIGINAL** | `models/timemixer/model.py` | No BHAI equivalent. Unique canonical asset. |
| `models/ensemble/meta_learner.py` | `climatedt/ml/models/forecasting/ensemble_model.py` | **MERGE** | `models/ensemble/meta_learner.py` | Original Ridge stacking + BHAI's ensemble approach. |
| `models/data_loader.py` | `climatedt/ml/data_loader.py` | **KEEP ORIGINAL** | `models/data_loader.py` | Original ClimateDataset/Scaler are complete. |
| `models/trainer.py` | `climatedt/ml/training.py` | **KEEP ORIGINAL** | `models/trainer.py` | Original training loop with early stopping. |
| `models/predictor.py` | _implicit_ | **KEEP ORIGINAL** | `models/predictor.py` | Original factory + inference pipeline. |
| `models/evaluator.py` | `climatedt/ml/evaluation.py` | **MERGE** | `models/evaluator.py` | Merge metric computations. |
| `models/registry.py` | `climatedt/ml/models.py` | **KEEP ORIGINAL** | `models/registry.py` | Original JSON-based registry. |
| `models/physics.py` | — | **KEEP ORIGINAL** | `models/physics.py` | Unique physical constraint validation. |
| `models/run_forecast.py` | _implicit_ | **KEEP ORIGINAL** | `models/run_forecast.py` | Original pipeline orchestrator. |
| — | `climatedt/ml/models/forecasting/xgboost_model.py` | **KEEP BHAI** | `models/xgboost/model.py` | New: XGBoost model. |
| — | `climatedt/ml/models/forecasting/prophet_model.py` | **KEEP BHAI** | `models/prophet/model.py` | New: Prophet model. |
| — | `climatedt/ml/models/forecasting/hyperparameter_tuning.py` | **KEEP BHAI** | `models/tuning.py` | New: hyperparameter optimization. |
| — | `climatedt/ml/features.py` | **KEEP BHAI** | `models/features.py` | New: feature engineering for ML. |

### 2.9 Data Pipeline

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `pipeline/run_pipeline.py` | — | **KEEP ORIGINAL** | `pipeline/run_pipeline.py` | No BHAI equivalent. Unique canonical asset. |
| `pipeline/download.py` | `climatedt/ingestion/` (connectors) | **KEEP ORIGINAL** | `pipeline/download.py` | Original NASA POWER API download is different from BHAI's scheduled ingestion. Both serve different purposes. |
| `pipeline/validate.py` | `climatedt/ingestion/quality.py` | **MERGE** | `pipeline/validate.py` | Merge quality check patterns. |
| `pipeline/clean.py` | — | **KEEP ORIGINAL** | `pipeline/clean.py` | No BHAI equivalent. |
| `pipeline/features.py` | — | **KEEP ORIGINAL** | `pipeline/features.py` | Original 20 features are domain-tuned. |
| `pipeline/export.py` | — | **KEEP ORIGINAL** | `pipeline/export.py` | Original train/val/test split. |
| `pipeline/sources/nasa_power.py` | `climatedt/ingestion/` | **KEEP ORIGINAL** | `pipeline/sources/nasa_power.py` | Different purpose (batch ETL vs streaming ingestion). |

### 2.10 Data Ingestion (New)

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| — | `climatedt/ingestion/imd_connector.py` | **KEEP BHAI** | `ingestion/imd_connector.py` | New: India Meteorological Department connector. |
| — | `climatedt/ingestion/era5_connector.py` | **KEEP BHAI** | `ingestion/era5_connector.py` | New: Copernicus ERA5 reanalysis connector. |
| — | `climatedt/ingestion/openmeteo_connector.py` | **KEEP BHAI** | `ingestion/openmeteo_connector.py` | New: Open-Meteo API connector. |
| — | `climatedt/ingestion/orchestrator.py` | **KEEP BHAI** | `ingestion/orchestrator.py` | New: ingestion orchestrator. |
| — | `climatedt/ingestion/scheduler.py` | **KEEP BHAI** | `ingestion/scheduler.py` | New: APScheduler-based scheduling. |
| — | `climatedt/ingestion/quality.py` | **KEEP BHAI** | `ingestion/quality.py` | New: data quality checks. |
| — | `climatedt/ingestion/location_registry.py` | **KEEP BHAI** | `ingestion/location_registry.py` | New: location management. |
| — | `climatedt/ingestion/base.py` | **KEEP BHAI** | `ingestion/base.py` | New: abstract connector base. |

### 2.11 Feedback Loop (New)

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| — | `climatedt/feedback/capture.py` | **KEEP BHAI** | `feedback/capture.py` | New: feedback capture service. |
| — | `climatedt/feedback/analysis.py` | **KEEP BHAI** | `feedback/analysis.py` | New: feedback analysis (stats, trends). |
| — | `climatedt/feedback/storage.py` | **KEEP BHAI** | `feedback/storage.py` | New: feedback store. |
| — | `climatedt/feedback/adaptation.py` | **KEEP BHAI** | `feedback/adaptation.py` | New: model weight adjustment from feedback. |
| — | `climatedt/feedback/online_learning.py` | **KEEP BHAI** | `feedback/online_learning.py` | New: online learning from feedback. |

### 2.12 Runtime (New)

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| — | `runtime/runtime.py` | **KEEP BHAI** | `runtime/runtime.py` | New: AgentRuntime orchestrator. |
| — | `runtime/blackboard.py` | **KEEP BHAI** | `runtime/blackboard.py` | New: thread-safe versioned state store. |
| — | `runtime/event_bus.py` | **KEEP BHAI** | `runtime/event_bus.py` | New: pub/sub event system. |
| — | `runtime/pipeline/engine.py` | **KEEP BHAI** | `runtime/pipeline/engine.py` | New: DAG-based pipeline engine. |
| — | `runtime/workflow/engine.py` | **KEEP BHAI** | `runtime/workflow/engine.py` | New: workflow engine. |
| — | `runtime/cache/` | **KEEP BHAI** | `runtime/cache/` | New: multi-strategy caching. |
| — | `runtime/providers/` | **KEEP BHAI** | `runtime/providers/` | New: provider system. |
| — | `runtime/capabilities/` | **KEEP BHAI** | `runtime/capabilities/` | New: capability system. |
| — | `runtime/lifecycle.py` | **KEEP BHAI** | `runtime/lifecycle.py` | New: runtime lifecycle states. |
| — | `runtime/observability.py` | **KEEP BHAI** | `runtime/observability.py` | New: metrics and logging. |
| — | `runtime/reliability.py` | **KEEP BHAI** | `runtime/reliability.py` | New: circuit breaker, retry. |
| — | `runtime/tracing.py` | **KEEP BHAI** | `runtime/tracing.py` | New: distributed tracing. |
| — | `runtime/plugins/` | **KEEP BHAI** | `runtime/plugins/` | New: plugin system. |
| — | `runtime/agents/` | **KEEP BHAI** | `runtime/agents/` | New: agent base classes. |

### 2.13 Deployment Infrastructure

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `deployment/docker/Dockerfile.gateway` | `Dockerfile` | **MERGE** | `deployment/docker/Dockerfile.gateway` | Merge BHAI's multi-stage build and resource limits. |
| `deployment/docker/Dockerfile.forecast` | `Dockerfile.forecast` | **MERGE** | `deployment/docker/Dockerfile.forecast` | Merge BHAI's health checks and resource limits. |
| `deployment/docker/Dockerfile.twin_state_mgr` | `Dockerfile.twin` | **MERGE** | `deployment/docker/Dockerfile.twin_state_mgr` | Merge BHAI's production hardening. |
| `deployment/docker/Dockerfile.dashboard` | `Dockerfile.dashboard` | **MERGE** | `deployment/docker/Dockerfile.dashboard` | Merge BHAI's improvements. |
| `deployment/docker/Dockerfile.copilot` | `Dockerfile.copilot` | **MERGE** | `deployment/docker/Dockerfile.copilot` | Merge both. |
| `deployment/docker/Dockerfile.rag` | — | **KEEP ORIGINAL** | `deployment/docker/Dockerfile.rag` | No BHAI equivalent. |
| `deployment/docker/Dockerfile.risk` | `Dockerfile.risk` | **MERGE** | `deployment/docker/Dockerfile.risk` | Merge both. |
| `deployment/docker/Dockerfile.scenario` | `Dockerfile.scenario` | **MERGE** | `deployment/docker/Dockerfile.scenario` | Merge both. |
| `deployment/docker/Dockerfile.ollama` | — | **KEEP ORIGINAL** | `deployment/docker/Dockerfile.ollama` | No BHAI equivalent. |
| — | `Dockerfile.base` | **KEEP BHAI** | `deployment/docker/Dockerfile.base` | New: shared base image pattern. |
| — | `Dockerfile.scheduler` | **KEEP BHAI** | `deployment/docker/Dockerfile.scheduler` | New: ingestion scheduler. |
| — | `Dockerfile.report` | **KEEP BHAI** | `deployment/docker/Dockerfile.report` | New: report generator service. |
| `docker-compose.yml` | `docker-compose.yml` | **MERGE** | `docker-compose.yml` | Keep canonical 9-service layout. Add runtime, ingestion scheduler, feedback as new services. Import BHAI's resource limits and production overrides. |
| — | `docker-compose.override.yml` | **KEEP BHAI** | `deployment/compose/docker-compose.override.yml` | New: dev mode with hot-reload. |
| — | `docker-compose.prod.yml` | **KEEP BHAI** | `deployment/compose/docker-compose.prod.yml` | New: production security hardening. |
| `deployment/monitoring/prometheus.yml` | — | **KEEP ORIGINAL** | `deployment/monitoring/prometheus.yml` | No BHAI equivalent. Unique canonical asset. |
| `deployment/monitoring/grafana/` | — | **KEEP ORIGINAL** | `deployment/monitoring/grafana/` | No BHAI equivalent. Unique canonical asset. |
| `deployment/configs/nginx.conf` | — | **KEEP ORIGINAL** | `deployment/configs/nginx.conf` | No BHAI equivalent. Unique canonical asset. |
| `deployment/scripts/startup.sh` | — | **KEEP ORIGINAL** | `deployment/scripts/startup.sh` | No BHAI equivalent. |
| `deployment/scripts/shutdown.sh` | — | **KEEP ORIGINAL** | `deployment/scripts/shutdown.sh` | No BHAI equivalent. |
| `deployment/scripts/demo.sh` | — | **KEEP ORIGINAL** | `deployment/scripts/demo.sh` | No BHAI equivalent. |
| `deployment/scripts/health_check.sh` | — | **KEEP ORIGINAL** | `deployment/scripts/health_check.sh` | No BHAI equivalent. |
| `deployment/health/health_check.py` | `scripts/healthcheck.py` | **MERGE** | `deployment/health/health_check.py` | Merge both health check patterns. |
| `deployment/cd/deploy.sh` | — | **KEEP ORIGINAL** | `deployment/cd/deploy.sh` | No BHAI equivalent. |
| `.github/workflows/ci.yml` | — | **KEEP ORIGINAL** | `.github/workflows/ci.yml` | No BHAI equivalent. |
| `.github/workflows/deploy.yml` | — | **KEEP ORIGINAL** | `.github/workflows/deploy.yml` | No BHAI equivalent. |

### 2.14 Configuration & Build

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `pyproject.toml` | `pyproject.toml` | **MERGE** | `pyproject.toml` | Merge all BHAI dependencies (httpx, aiohttp, APScheduler, prophet, xgboost, etc.) into canonical. Keep canonical's tool configs (ruff, pytest, coverage, mypy, tox, isort, black). |
| `Makefile` | — | **KEEP ORIGINAL** | `Makefile` | Add targets for new services. |
| `ruff.toml` | — | **KEEP ORIGINAL** | `ruff.toml` | No BHAI equivalent. |
| `pytest.ini` | — | **KEEP ORIGINAL** | `pytest.ini` | No BHAI equivalent. |
| `.pre-commit-config.yaml` | — | **KEEP ORIGINAL** | `.pre-commit-config.yaml` | No BHAI equivalent. |
| `.env` | `.env` | **MERGE** | `.env` | Merge env var patterns. |
| `.gitignore` | `.gitignore` | **MERGE** | `.gitignore` | Merge ignore patterns. |
| `config/data_config.yaml` | `config/schedules.yaml` | **KEEP ORIGINAL** | `config/data_config.yaml` | Original data pipeline config. Add BHAI's schedules.yaml. |

### 2.15 Tests

| Original Module | BHAI Equivalent | Decision | Final Destination | Rationale |
|---|---|---|---|---|
| `tests/` (existing) | `tests/` (BHAI) | **MERGE** | `tests/` | Merge both test suites. Original tests cover: backend, pipeline, models, simulator, dashboard, risk, knowledge, copilot. BHAI tests cover: api_gateway, copilot, dashboard, feedback, ingestion, infra, ml, rag, reports, risk, scenario, twin, storage. |
| — | `tests/test_infra/` | **KEEP BHAI** | `tests/test_infra/` | New: infrastructure validation tests (docker-compose, Dockerfiles, .env). |
| — | `tests/test_feedback/` | **KEEP BHAI** | `tests/test_feedback/` | New: feedback loop tests. |
| — | `tests/test_ingestion/` | **KEEP BHAI** | `tests/test_ingestion/` | New: ingestion tests. |
| — | `tests/test_api_gateway/` | **KEEP BHAI** | `tests/test_api_gateway/` | New: gateway tests. |
| — | `tests/test_scenario/` (BHAI) | **MERGE** | `tests/test_scenario/` | Merge with original scenario tests. |
| — | `tests/test_twin/` (BHAI) | **MERGE** | `tests/test_twin/` | Merge with original twin tests. |
| — | `tests/test_risk/` (BHAI) | **MERGE** | `tests/test_risk/` | Merge with original risk tests. |
| — | `tests/test_rag/` (BHAI) | **MERGE** | `tests/test_rag/` | Merge with original knowledge tests. |
| — | `tests/test_ml/` (BHAI) | **MERGE** | `tests/test_ml/` | Merge with original model tests. |

### 2.16 Data Models (BHAI models that need new home)

| BHAI Module | Decision | Final Destination | Rationale |
|---|---|---|---|
| `climatedt/models/weather.py` | **KEEP BHAI** | `simulator/models/weather.py` | New: WeatherObservation model. |
| `climatedt/models/era5.py` | **KEEP BHAI** | `ingestion/models/era5.py` | New: ERA5 data model. |
| `climatedt/models/imd.py` | **KEEP BHAI** | `ingestion/models/imd.py` | New: IMD data model. |
| `climatedt/models/feedback.py` | **KEEP BHAI** | `feedback/models.py` | New: feedback data models. |
| `climatedt/models/ingestion.py` | **KEEP BHAI** | `ingestion/models/schema.py` | New: ingestion job models. |
| `climatedt/models/rag.py` | **KEEP BHAI** | `knowledge/models/rag_models.py` | New: RAG document models. |
| `climatedt/models/baseline.py` | **KEEP BHAI** | `simulator/models/baseline.py` | New: baseline data models. |

---

## 3. Dependency Graph

```
Phase A: Foundation (pyproject.toml, configs, Makefile)
  │
  ├──► Phase B: Runtime (no dependencies — import BHAI runtime/ as-is)
  │
  ├──► Phase C: API Gateway (depends on A)
  │     └── routes/*, middleware, models, deps, config
  │
  ├──► Phase D: Digital Twin Core (depends on A)
  │     ├── simulator/engine/ — merge scenario engine + monte carlo/perturbation/ensemble
  │     ├── simulator/twin/ — import graph, conflict, anomaly, reconciliation
  │     ├── simulator/repository/ — import feature store, dataset registry
  │     └── simulator/entities/ — merge climate entity + twin state models
  │
  ├──► Phase E: Dashboard (depends on C)
  │     ├── pages/ — restore original 7 + import 3 new (Feedback, Knowledge, Twin)
  │     ├── charts/ — keep original
  │     ├── components/ — keep original  
  │     ├── maps/ — keep original
  │     └── services/ — merge api_client + utils.py
  │
  ├──► Phase F: ML Models (depends on A)
  │     ├── models/*/ — keep 7 original architectures
  │     ├── models/xgboost/ — new import
  │     ├── models/prophet/ — new import
  │     └── models/tuning.py — new import
  │
  ├──► Phase G: Copilot (depends on D, H)
  │     ├── agent/ — merge intent classification (import BHAI's)
  │     ├── llm/ — merge Ollama client (import BHAI's)
  │     └── workflows/ — merge orchestrator patterns
  │
  ├──► Phase H: RAG (depends on A)
  │     ├── embeddings/ — merge multi-strategy fallback
  │     ├── retriever/ — add hybrid search (BM25)
  │     └── vector_store/ — add collection management
  │
  ├──► Phase I: Risk (depends on D)
  │     └── scoring/ — add agriculture_risk model
  │
  ├──► Phase J: Tests (depends on A-I)
  │     └── tests/ — merge all test suites, fix import paths
  │
  ├──► Phase K: Infrastructure (depends on A-I)
  │     ├── docker-compose.yml — add new services
  │     ├── Dockerfile.* — merge patterns
  │     └── deployment/ — keep monitoring, nginx, CI/CD, scripts
  │
  └──► Phase L: Documentation (depends on A-K)
        └── reports/ + docs/ — merge documentation
```

### Parallelism Opportunities

| Group | Phases | Can Run In Parallel? |
|-------|--------|---------------------|
| 1 | A (Foundation) | Starting point, no parallelism |
| 2 | B (Runtime), C (Gateway), D (Twin), F (ML), H (RAG) | **YES** — all depend only on A |
| 3 | E (Dashboard), I (Risk) | Depend on C and D respectively → run after those complete |
| 4 | G (Copilot) | Depends on D and H → run after those complete |
| 5 | J (Tests) | Depends on all code phases → run after A-I complete |
| 6 | K (Infrastructure) | Depends on all code phases → run after A-I complete |
| 7 | L (Documentation) | Depends on everything → final phase |

---

## 4. New Folder Structure (Post-Migration)

```
climate-digital-twin/
├── backend/                    ← Phase C (REPLACED)
├── config/                     ← Phase A (KEPT + schedules.yaml)
├── copilot/                    ← Phase G (MERGED)
├── dashboard/                  ← Phase E (MERGED)
├── data/                       ← (KEPT)
├── deployment/                 ← Phase K (MERGED)
├── feedback/                   ← Phase I (NEW from BHAI)
├── ingestion/                  ← Phase D (NEW from BHAI)
├── knowledge/                  ← Phase H (MERGED)
├── models/                     ← Phase F (MERGED + XGBoost/Prophet)
├── pipeline/                   ← (KEPT ORIGINAL)
├── reports/                    ← Phase L (MERGED)
├── risk/                       ← Phase I (MERGED)
├── runtime/                    ← Phase B (NEW from BHAI)
├── scripts/                    ← (KEPT)
├── simulator/                  ← Phase D (MERGED + new twin features)
├── tests/                      ← Phase J (MERGED)
├── docs/                       ← Phase L (NEW from BHAI)
├── .github/workflows/          ← Phase K (KEPT)
├── docker-compose.yml          ← Phase K (MERGED)
├── pyproject.toml              ← Phase A (MERGED)
├── Makefile                    ← Phase A (UPDATED)
├── ruff.toml                   ← (KEPT)
├── pytest.ini                  ← (KEPT)
├── .pre-commit-config.yaml     ← (KEPT)
└── ARCHITECTURE_MIGRATION.md   ← THIS FILE
```

---

## 5. Service Map (Post-Migration)

| Service | Port | Dockerfile | Source |
|---|---|---|---|
| twin-state-mgr | 8001 | deployment/docker/Dockerfile.twin_state_mgr | simulator/ (MERGED) |
| scenario-engine | 8002 | deployment/docker/Dockerfile.scenario | simulator/scenarios/ (MERGED) |
| risk-engine | 8003 | deployment/docker/Dockerfile.risk | risk/ (MERGED) |
| rag-service | 8004 | deployment/docker/Dockerfile.rag | knowledge/ (MERGED) |
| copilot-agent | 8005 | deployment/docker/Dockerfile.copilot | copilot/ (MERGED) |
| forecast-engine | 8006 | deployment/docker/Dockerfile.forecast | models/ + backend/services/forecast/ (MERGED) |
| fastapi-gateway | 8000 | deployment/docker/Dockerfile.gateway | backend/api/ (REPLACED) |
| streamlit-dashboard | 8501 | deployment/docker/Dockerfile.dashboard | dashboard/ (MERGED) |
| ollama | 11434 | deployment/docker/Dockerfile.ollama | (KEPT) |
| ingestion-scheduler | 8010 | deployment/docker/Dockerfile.scheduler | ingestion/ (NEW) |
| report-service | 8007 | deployment/docker/Dockerfile.report | reports/ (NEW) |
| runtime | (internal) | — | runtime/ (NEW, library) |

---

## 6. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **BHAI test imports fail** after relocating code to canonical paths | **HIGH** | Phase J must update all import paths and run full test suite before declaring completion |
| **Docker compose restructure breaks** existing deployment scripts | **MEDIUM** | Phase K test with `docker compose build && docker compose up` |
| **Model checkpoint formats differ** between BHAI (XGBoost) and original (PyTorch) | **LOW** | They can coexist — models are loaded by name in predictor.py |
| **BHAI's climatedt/ package** has deep internal imports that fail when relocated | **MEDIUM** | Use `__init__.py` re-exports and import adapters |
| **Dashboard page renumbering** breaks bookmark URLs | **LOW** | Keep original page numbers (01-07). New pages get 08-09. |
| **Copilot tool clients** need updated service URLs after migration | **LOW** | Service URLs are configurable via environment variables |
| **Test count regression** — some BHAI tests may be lost | **HIGH** | Track total test count before and after each phase |
| **Runtime tests depend on BHAI's pyproject.toml** dependencies | **MEDIUM** | Merge all BHAI deps into canonical pyproject.toml in Phase A |

---

## 7. Acceptance Criteria

The migration is complete when these conditions are all met:

1. **No original functionality lost** — All original 7 dashboard pages, 7 ML models, data pipeline, risk engine with SHAP, RAG with FAISS, copilot with multi-agent, deployment with monitoring/nginx/CI-CD all work as before
2. **New capabilities added** — Runtime, ingestion, feedback loop, entity graph, conflict resolution, anomaly detection, agriculture risk, hybrid RAG search, XGBoost/Prophet models are all integrated and functional
3. **All tests pass** — Combined test suite (original + BHAI) achieves ≥1000 passing tests
4. **Docker compose builds** — `docker compose build` succeeds for all services
5. **No import errors** — Every Python module can be imported without errors
6. **No placeholders/TODOs remain** from the migration process
7. **Documentation updated** — ARCHITECTURE_MIGRATION.md superseded by final docs in reports/

---

*End of Phase 0 document. Begin Phase A when this is approved.*
