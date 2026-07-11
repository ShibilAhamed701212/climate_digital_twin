# Folder Structure

> Repository tree as of July 2026. ~262 Python files, ~17,354 LOC.

```
climate-digital-twin/
├── .github/
│   └── workflows/           # GitHub Actions (minimal: pytest on push)
├── api/                     # FastAPI forecasting service
│   ├── main.py              # FastAPI app, /predict, /models, /health
│   └── requirements.txt
├── app/                     # Streamlit dashboard
│   ├── main.py              # Dashboard entry point
│   ├── config.py            # App configuration
│   ├── pages/               # 10 page modules
│   │   ├── 01_Forecast.py   # Live
│   │   ├── 02_Twin.py       # Live
│   │   ├── 03_Risk.py       # Live
│   │   ├── 04_Scenario.py   # Live
│   │   ├── 05_Maps.py       # Live
│   │   ├── 06_About.py      # Live
│   │   ├── 07_Home.py       # Live
│   │   ├── 08_Knowledge.py  # ⚠️ MOCK - no backend connectivity
│   │   ├── 09_Feedback.py   # ⚠️ MOCK - no backend connectivity
│   │   └── 10_BHAI_State.py # ⚠️ MOCK - placeholder content
│   ├── components/          # Reusable chart/map components
│   └── utils/               # Dashboard utilities
├── config/
│   ├── config.yaml          # 15 sample Karnataka districts
│   ├── risk.yaml            # Risk scoring weights
│   ├── scenarios.yaml       # Scenario definitions
│   └── model_config.yaml    # Model hyperparameters
├── copilot/                 # AI copilot (mock)
│   ├── main.py              # FastAPI app
│   ├── intent_classifier.py # Keyword-based classification
│   ├── executor.py          # Tool dispatcher
│   ├── generator.py         # ⚠️ Template-based mock responses
│   ├── conversation.py      # In-memory conversation state
│   └── requirements.txt
├── data/
│   ├── raw/                 # Synthetic raw data (.parquet)
│   ├── processed/           # Synthetic processed data (.parquet)
│   ├── synthetic/           # Generator scripts
│   └── documents/           # 15 demo documents for RAG
├── digital_twin/
│   ├── main.py              # FastAPI app
│   ├── entity.py            # ClimateEntity immutable dataclass
│   ├── state_manager.py     # Append-only versioned state
│   ├── event_bus.py         # Pub/sub event system
│   ├── repository.py        # Parquet storage per location
│   └── requirements.txt
├── docker/
│   ├── docker-compose.yml   # 8 services
│   ├── Dockerfile.api
│   ├── Dockerfile.app
│   ├── Dockerfile.twin
│   ├── Dockerfile.scenario
│   ├── Dockerfile.risk
│   ├── Dockerfile.rag
│   ├── Dockerfile.copilot
│   └── nginx/
│       └── default.conf     # Reverse proxy config
├── explainability/
│   ├── main.py              # FastAPI app
│   ├── shap_explainer.py    # ⚠️ Deterministic synthetic SHAP
│   └── requirements.txt
├── models/                  # PyTorch forecasting models
│   ├── baseline_mlp.py      # Trained on synthetic data
│   ├── lstm_model.py        # Trained on synthetic data (best RMSE ~4.53)
│   ├── transformer_model.py # Trained on synthetic data
│   ├── patchtst.py          # ⚠️ STUB - class definition only
│   ├── timemixer.py         # ⚠️ STUB - class definition only
│   ├── itransformer.py      # ⚠️ STUB - class definition only
│   ├── ensemble.py          # ⚠️ Ridge regression wrapper (minimal)
│   └── checkpoints/         # Saved model weights (trained on synthetic)
├── rag/
│   ├── main.py              # FastAPI app
│   ├── index_builder.py     # FAISS index construction
│   ├── retriever.py         # Vector search (top-k, threshold)
│   ├── generator.py         # ⚠️ Mock answer generation
│   ├── document_loader.py   # Multi-format loader
│   └── requirements.txt
├── reports/                 # This documentation (57 files)
│   └── REPORT_INDEX.md
├── risk/
│   ├── main.py              # FastAPI app
│   ├── heat_risk.py         # Heat scoring module
│   ├── flood_risk.py        # Flood scoring module
│   ├── drought_risk.py      # Drought scoring module
│   ├── composite_risk.py    # Aggregated scoring
│   └── requirements.txt
├── scenario_engine/
│   ├── main.py              # FastAPI app
│   ├── scenarios.py         # Scenario types and presets
│   ├── simulator.py         # Deterministic simulation
│   └── requirements.txt
├── scripts/
│   ├── seed_data.py         # Generate synthetic data
│   ├── train_models.py      # Train on synthetic data
│   └── run_all.py           # Start all services
├── tests/
│   ├── test_dashboard.py    # 109 tests (18 known env failures)
│   └── ...
├── tools/                   # Development utilities
└── requirements.txt         # Root-level dependencies
```

---

## By the Numbers

| Metric | Count | Notes |
|--------|-------|-------|
| Python files | ~262 | Includes models, tests, tools, scripts |
| Total LOC | ~17,354 | Rough count including generated/legacy files |
| Test files | ~30+ | Dashboard-focused; model/API/RAG/Copilot untested |
| Docker services | 8 | + external Ollama dependency |
| Configuration files | 4 | YAML + dashboard config |
| Report files | 57 | These documentation files |
