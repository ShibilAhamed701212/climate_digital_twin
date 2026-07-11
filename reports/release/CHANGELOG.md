# CHANGELOG

> Complete development history from empty repository to hackathon submission.

---

## v0.1.0 (2026-07-xx)

### Added
- Full Streamlit dashboard with 10 pages (7 live, 3 mock)
- Docker Compose with 8 services + Ollama dependency
- 7 model architectures (3 trained, 3 stubs, 1 mock ensemble)
- Digital twin with immutable entities, state versioning, event bus
- Scenario engine with 11 preset scenarios
- Risk scoring with 4 modules + composite
- RAG pipeline with FAISS and sentence-transformers
- Copilot with 4-stage pipeline (mock responses)
- Synthetic SHAP explainer
- 109 dashboard tests

### Changed
- All reports rewritten for honesty (this update)

### Fixed
- Numerous during development (not tracked)

---

## v0.0.5 (2026-06-xx)

### Added
- Streamlit dashboard pages (Home, Forecast, Twin, Risk, Scenario, Maps, About)
- API integration layer for dashboard
- Interactive charts with Plotly
- Folium risk maps
- Dashboard configuration system

### Changed
- API responses formatted for dashboard consumption

---

## v0.0.4 (2026-06-xx)

### Added
- Model training pipeline (MLP, LSTM, Transformer)
- Sliding window data loader
- PhysicsValidator for prediction constraints
- Training with early stopping and LR scheduling
- Model checkpoint registry
- Synthetic data generator (np.random.seed(42))

### Changed
- Data pipeline switched from real API to synthetic generation

---

## v0.0.3 (2026-05-xx)

### Added
- Docker Compose orchestration
- Dockerfiles for all services
- Nginx reverse proxy
- RAG pipeline (FAISS + sentence-transformers)
- Document loading (MD, TXT, CSV, JSON, PDF stub)
- Recursive chunking strategy

---

## v0.0.2 (2026-05-xx)

### Added
- Forecasting model classes (MLP, LSTM, Transformer)
- Baseline implementations for PatchTST, TimeMixer, iTransformer
- Risk scoring modules (heat, flood, drought, composite)
- Risk configuration system
- Scenario engine (temperature, rainfall, monsoon, extreme, combined)

---

## v0.0.1 (2026-05-xx)

### Added
- Project scaffold
- Configuration file structure
- Synthetic data generation scripts
- Basic API structure
- Digital twin core (entity, state manager, event bus)
- Initial test structure
- README and project documentation
