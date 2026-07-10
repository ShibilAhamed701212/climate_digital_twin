# Folder Structure

```
climate-digital-twin/
├── AGENT.md
├── Makefile
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── pytest.ini
├── ruff.toml
├── .dockerignore
├── .gitignore
├── .pre-commit-config.yaml
│
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint → Test (matrix 3.10/3.12) → Docker
│       └── deploy.yml                 # CD on version tags
│
├── backend/
│   ├── __init__.py
│   ├── core/
│   │   └── __init__.py
│   └── api/
│       ├── __init__.py
│       ├── main.py                    # FastAPI gateway /health endpoint
│       ├── models/
│       │   └── __init__.py
│       ├── routes/
│       │   └── __init__.py
│       └── services/
│           └── __init__.py
│
├── config/
│   └── data_config.yaml               # Pipeline settings, Karnataka bounds, NASA POWER config
│
├── copilot/
│   ├── __init__.py
│   ├── config_loader.py               # YAML config loader with caching
│   ├── models.py                      # IntentType, Plan, ToolCall, CopilotResponse dataclasses
│   ├── agent/
│   │   ├── __init__.py
│   │   └── intent_agent.py            # Intent classification (8 types)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                    # Copilot FastAPI /health endpoint
│   │   └── copilot_api.py            # Facade: ask(), new_conversation(), get_history()
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── forecast_client.py
│   │   ├── rag_client.py
│   │   ├── report_client.py
│   │   ├── risk_client.py
│   │   ├── scenario_client.py
│   │   └── twin_client.py
│   ├── configs/
│   │   ├── __init__.py
│   │   └── copilot.yaml               # LLM config, memory, tool registry
│   ├── llm/
│   │   ├── __init__.py
│   │   └── ollama_client.py           # Ollama API wrapper
│   ├── memory/
│   │   ├── __init__.py
│   │   └── conversation_memory.py     # Buffer window (10 turns, 60min expiry)
│   ├── planner/
│   │   ├── __init__.py
│   │   └── planner.py                 # 8 intent-specific planners
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── intent.txt                 # Prompt: intent classification
│   │   ├── planner.txt                # Prompt: tool planning
│   │   ├── generator.txt              # Prompt: response generation
│   │   └── error.txt                  # Prompt: error handling
│   ├── reports/
│   │   ├── __init__.py
│   │   └── conversation_report.py     # JSON + Markdown conversation reports
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseTool ABC (run/validate/describe/health_check)
│   │   ├── registry.py               # ToolRegistry with enable/disable
│   │   ├── forecast_tool.py
│   │   ├── rag_tool.py
│   │   ├── report_tool.py
│   │   ├── risk_tool.py
│   │   ├── scenario_tool.py
│   │   └── twin_tool.py
│   ├── ui/
│   │   └── __init__.py
│   └── workflows/
│       ├── __init__.py
│       ├── executor.py                # Per-step tool execution with timing
│       ├── generator.py               # 7 intent-specific response formatters
│       └── orchestrator.py            # classify→plan→execute→generate→memorize
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py                         # Streamlit entry point
│   ├── assets/
│   │   └── style.css                  # Custom CSS
│   ├── charts/
│   │   ├── __init__.py
│   │   ├── comparison.py              # Before/after bar charts
│   │   ├── distribution.py            # Histograms, scatter with OLS
│   │   ├── risk_trends.py             # Risk gauge, SHAP waterfall
│   │   └── time_series.py             # Line charts with confidence bands
│   ├── components/
│   │   ├── __init__.py
│   │   ├── cards.py                   # Metric/info cards, status badges
│   │   ├── filters.py                 # Scenario parameter sliders
│   │   └── sidebar.py                 # District/location/variable/horizon selectors
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py                  # API URLs, map defaults, color schemes
│   ├── maps/
│   │   ├── __init__.py
│   │   ├── climate_map.py             # Climate overlay with CircleMarkers
│   │   └── comparison_map.py          # Before/after with PolyLine connectors
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── 01_climate_overview.py     # Overview page
│   │   ├── 02_forecast_viewer.py      # Forecast page
│   │   ├── 03_twin_state.py           # Twin state page (4 tabs)
│   │   ├── 04_scenario_simulator.py   # Scenario simulator page
│   │   ├── 05_climate_risk.py         # Climate risk page (4 tabs)
│   │   ├── 06_reports.py             # Reports page (4 tabs)
│   │   └── 07_copilot_chat.py        # AI Copilot chat page
│   ├── services/
│   │   ├── __init__.py
│   │   └── api_client.py              # Synthetic data fallback for all endpoints
│   └── themes/
│       └── __init__.py
│
├── data/
│   ├── raw/
│   │   ├── rainfall.parquet
│   │   ├── maxtemp.parquet
│   │   └── mintemp.parquet
│   ├── interim/
│   │   ├── cleaned_data.parquet
│   │   └── featured_data.parquet
│   ├── processed/
│   │   ├── training.csv
│   │   ├── validation.csv
│   │   └── testing.csv
│   ├── twin_store/
│   │   └── KA-E2E-001.parquet
│   └── test_twin_store/
│       ├── KA-BLR-001.parquet
│       └── KA-MYS-001.parquet
│
├── deployment/
│   ├── cd/
│   │   └── deploy.sh                  # CD deployment script
│   ├── compose/
│   │   └── monitoring.yml             # Standalone monitoring overlay
│   ├── configs/
│   │   ├── .env.example               # 14 environment variables
│   │   └── nginx.conf                 # Reverse proxy
│   ├── docker/
│   │   ├── Dockerfile.twin_state_mgr
│   │   ├── Dockerfile.forecast
│   │   ├── Dockerfile.scenario
│   │   ├── Dockerfile.risk
│   │   ├── Dockerfile.rag
│   │   ├── Dockerfile.copilot
│   │   ├── Dockerfile.gateway
│   │   └── Dockerfile.dashboard
│   ├── docs/
│   │   └── architecture.md           # Architecture documentation
│   ├── health/
│   │   └── health_check.py           # Python health check utility
│   ├── monitoring/
│   │   ├── prometheus.yml             # Scrape config (7 targets)
│   │   └── grafana/
│   │       ├── dashboard.yml          # Provisioning config
│   │       ├── datasources/
│   │       │   └── datasource.yml     # Prometheus data source
│   │       └── dashboards/
│   │           └── service-health.json # 6-panel dashboard
│   └── scripts/
│       ├── demo.sh                    # 6-step demo walkthrough
│       ├── health_check.sh            # Shell-based health verification
│       ├── shutdown.sh                # Graceful docker compose down
│       └── startup.sh                 # Build + start + validate
│
├── docs/
│   ├── KNOWN_FAILURES.md              # 18 known test failures baseline
│   ├── phase-1-scope.md
│   ├── phase-2-data-pipeline.md
│   ├── phase-3-Forecasting-Engine.md
│   ├── phase-4-digital-twin.md
│   ├── phase-5-dashboard.md
│   ├── phase-6-scenario-engine.md
│   ├── phase-7-risk-explainability.md
│   ├── phase-8-rag-knowledge-base.md
│   ├── phase-9-climate-copilot.md
│   ├── phase-10-deployment.md
│   └── superpowers/
│       └── specs/
│           └── 2026-06-27-climate-digital-twin-v2-architecture.md
│
├── knowledge/
│   ├── __init__.py
│   ├── config_loader.py               # RAG config loader with defaults
│   ├── models.py                      # Document, Chunk, SearchResult dataclasses
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                    # RAG FastAPI /health endpoint
│   │   └── search_api.py             # KnowledgeAPI facade
│   ├── chunkers/
│   │   ├── __init__.py
│   │   └── text_chunker.py            # Recursive chunking (700/120 overlap)
│   ├── configs/
│   │   ├── __init__.py
│   │   └── rag.yaml                   # Chunking, embedding, retrieval config
│   ├── documents/
│   │   ├── government/
│   │   │   └── karnataka_climate_profile.md
│   │   ├── imd/
│   │   │   └── imd_weather_data.md
│   │   ├── isro/
│   │   │   └── insat_satellite_products.md
│   │   ├── research/
│   │   │   └── climate_forecasting_methods.md
│   │   └── risk/
│   │       └── climate_risk_assessment.md
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── embedding_model.py         # sentence-transformers + dummy fallback
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseLoader ABC
│   │   ├── csv_loader.py
│   │   ├── factory.py                # Extension-based dispatch
│   │   ├── json_loader.py
│   │   ├── md_loader.py
│   │   └── txt_loader.py
│   ├── pipelines/
│   │   ├── __init__.py
│   │   └── indexing_pipeline.py       # load→chunk→embed→store
│   ├── reports/
│   │   ├── __init__.py
│   │   └── index_report.py           # Summary, JSON, Markdown reports
│   ├── retriever/
│   │   ├── __init__.py
│   │   ├── context_builder.py         # LLM context, sectioned, dashboard format
│   │   └── semantic_search.py         # Search with threshold + metadata filter
│   └── vector_store/
│       ├── __init__.py
│       ├── faiss_store.py             # IndexFlatIP with metadata
│       ├── index.faiss
│       └── metadata.pkl
│
├── logs/
│   ├── copilot.log
│   └── forecast_pipeline.log
│
├── models/
│   ├── __init__.py
│   ├── data_loader.py                 # PyTorch Dataset/DataLoader with sliding windows
│   ├── evaluator.py                   # RMSE, MAE, R², sMAPE + plots
│   ├── physics.py                     # PhysicsValidator safety layer
│   ├── predictor.py                   # Prediction API with confidence intervals
│   ├── registry.py                    # Model registry (JSON metadata)
│   ├── run_forecast.py                # End-to-end orchestrator
│   ├── trainer.py                     # Training engine with early stopping
│   ├── baseline/
│   │   ├── __init__.py
│   │   └── model.py                   # MLP feed-forward
│   ├── checkpoints/
│   │   ├── baseline_best.pt
│   │   ├── lstm_best.pt
│   │   └── transformer_best.pt
│   ├── configs/
│   │   ├── __init__.py
│   │   └── model_config.yaml          # All 7 model hyperparameters
│   ├── ensemble/
│   │   ├── __init__.py
│   │   └── meta_learner.py            # Ridge regression ensemble
│   ├── exported/
│   │   └── transformer_best.pt        # TorchScript export
│   ├── itransformer/
│   │   ├── __init__.py
│   │   └── model.py                   # Feature-axis Transformer
│   ├── lstm/
│   │   ├── __init__.py
│   │   └── model.py                   # Stacked LSTM
│   ├── patchtst/
│   │   ├── __init__.py
│   │   └── model.py                   # Patch-embedded Transformer
│   ├── registry/
│   │   └── metadata.json              # Model registration metadata
│   └── timemixer/
│       ├── __init__.py
│       └── model.py                   # MLP-mixer with LayerNorm
│
├── pipeline/
│   ├── __init__.py
│   ├── clean.py                       # Missing value interpolation, outlier clipping
│   ├── download.py                    # DataDownloader with resume + synthetic fallback
│   ├── export.py                      # 70/15/15 split, CSV export
│   ├── features.py                    # 12 engineered features
│   ├── run_pipeline.py                # End-to-end orchestrator
│   ├── validate.py                    # Quality checks + JSON report
│   └── sources/
│       ├── __init__.py
│       └── nasa_power.py             # NASA POWER API wrapper
│
├── risk/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── contract.py               # RiskAPI abstract base class
│   │   └── main.py                   # Risk FastAPI /health endpoint
│   ├── configs/
│   │   ├── __init__.py
│   │   └── risk.yaml                  # Weights, thresholds, categories
│   ├── engine/
│   │   ├── __init__.py
│   │   └── risk_engine.py            # RiskEngine orchestrator
│   ├── explainability/
│   │   ├── __init__.py
│   │   ├── insights_engine.py        # Natural-language insights
│   │   └── shap_explainer.py         # Deterministic SHAP estimation
│   ├── models/
│   │   ├── __init__.py
│   │   └── risk_models.py            # HeatRisk, FloodRisk, DroughtRisk, CompositeRisk
│   ├── outputs/
│   │   └── __init__.py
│   ├── reports/
│   │   ├── __init__.py
│   │   └── report_generator.py       # JSON + Markdown reports
│   └── scoring/
│       ├── __init__.py
│       ├── composite_risk.py         # Weighted combination
│       ├── drought_risk.py           # Deficit-based scoring
│       ├── flood_risk.py             # Intensity + accumulation
│       └── heat_risk.py             # Temperature-based scoring
│
├── scripts/
│   ├── add_init_docstrings.py
│   ├── check_vector_store.py
│   ├── end_to_end_test.py             # 17-stage E2E pipeline test
│   ├── index_architecture_docs.py
│   ├── index_knowledge_base.py
│   ├── register_models.py
│   └── smoke_test_models.py
│
├── simulator/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── contract.py               # TwinAPI abstract contract
│   │   └── main.py                   # Twin state FastAPI /health endpoint
│   ├── configs/
│   │   ├── __init__.py
│   │   ├── scenario.yaml             # Scenario bounds and validation
│   │   └── twin_config.yaml          # Grid, storage, state, event config
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── scenario_engine.py        # Deterministic scenario simulation
│   │   └── twin_engine.py           # DigitalTwinEngine orchestrator
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── climate_entity.py        # Immutable ClimateEntity dataclass
│   │   └── state.py                 # StateType enum
│   ├── events/
│   │   ├── __init__.py
│   │   ├── event_bus.py             # Pub/sub with error isolation
│   │   └── events.py                # TwinEvent + 11 event types
│   ├── models/
│   │   ├── __init__.py
│   │   └── scenario_models.py       # ScenarioDefinition, SimulationResult, ScenarioRun
│   ├── outputs/
│   │   ├── __init__.py
│   │   └── output_generator.py      # JSON, CSV, Markdown export
│   ├── reports/
│   │   ├── __init__.py
│   │   └── report_generator.py      # Aggregate deltas report
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── base.py                  # TwinRepository ABC
│   │   └── parquet_repository.py    # Per-location Parquet with cache
│   ├── scenarios/
│   │   ├── __init__.py
│   │   ├── api.py                   # Scenario FastAPI /health endpoint
│   │   └── scenario_builder.py      # 11 preset definitions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scenario_service.py       # Full scenario lifecycle
│   │   └── twin_service.py          # Twin state coordination
│   ├── state_manager/
│   │   ├── __init__.py
│   │   ├── manager.py               # Append-only versioning
│   │   └── version.py              # Immutable Version dataclass
│   └── validators/
│       ├── __init__.py
│       └── scenario_validator.py    # Type-specific input validation
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Shared pytest fixtures
    ├── fixtures/
    │   └── __init__.py
    ├── integration/
    │   ├── __init__.py
    │   ├── conftest.py               # Integration fixtures
    │   ├── test_forecast.py          # 7 integration tests
    │   ├── test_pipeline.py          # 7 integration tests
    │   ├── test_scenario_service.py  # 9 integration tests
    │   └── test_twin_engine.py       # 8 integration tests
    ├── unit/
    │   ├── __init__.py
    │   ├── conftest.py               # Unit test fixtures
    │   ├── test_clean.py
    │   ├── test_copilot_api.py
    │   ├── test_copilot_config.py
    │   ├── test_copilot_executor.py
    │   ├── test_copilot_generator.py
    │   ├── test_copilot_intent.py
    │   ├── test_copilot_memory.py
    │   ├── test_copilot_models.py
    │   ├── test_copilot_orchestrator.py
    │   ├── test_copilot_planner.py
    │   ├── test_copilot_reports.py
    │   ├── test_copilot_tools.py
    │   ├── test_dashboard.py
    │   ├── test_data_loader.py
    │   ├── test_download.py
    │   ├── test_evaluator.py
    │   ├── test_export.py
    │   ├── test_features.py
    │   ├── test_models.py
    │   ├── test_physics.py
    │   ├── test_predictor.py
    │   ├── test_rag_api.py
    │   ├── test_rag_chunkers.py
    │   ├── test_rag_config.py
    │   ├── test_rag_embeddings.py
    │   ├── test_rag_loaders.py
    │   ├── test_rag_models.py
    │   ├── test_rag_pipeline.py
    │   ├── test_rag_reports.py
    │   ├── test_rag_retriever.py
    │   ├── test_rag_vector_store.py
    │   ├── test_risk_api.py
    │   ├── test_risk_engine.py
    │   ├── test_risk_explainability.py
    │   ├── test_risk_models.py
    │   ├── test_risk_reports.py
    │   ├── test_risk_scoring.py
    │   ├── test_scenario_builder.py
    │   ├── test_scenario_engine.py
    │   ├── test_scenario_models.py
    │   ├── test_scenario_outputs.py
    │   ├── test_scenario_validator.py
    │   ├── test_trainer.py
    │   ├── test_twin_entities.py
    │   ├── test_twin_events.py
    │   ├── test_twin_repository.py
    │   ├── test_twin_service.py
    │   ├── test_twin_state_manager.py
    │   └── test_validate.py
    ├── test_itransformer.py
    ├── test_meta_learner.py
    ├── test_patchtst.py
    ├── test_registry.py
    └── test_timemixer.py
```
