# Release Notes

> **All versions are pre-release (0.x). No stable release cut.**

---

## v0.1.0 (Current — Hackathon Demo)

**Date:** July 2026  
**Status:** Proof-of-Concept / Synthetic Data / Not Production-Ready

### What's Included
- Docker Compose with 8 services
- Synthetic data pipeline (np.random.seed(42))
- 3 trained forecasting models (MLP, LSTM, Transformer)
- Digital twin with state versioning
- Scenario engine (11 presets)
- Risk scoring (4 modules)
- RAG pipeline with FAISS (small corpus)
- Mock copilot (no LLM)
- Streamlit dashboard (10 pages, 3 mock)
- Deterministic SHAP (synthetic)

### Known Issues
- FAISS index starts empty
- Copilot returns mock responses
- Dashboard pages 08–10 are mock UIs
- 18 test failures in certain environments
- No authentication
- All data synthetic

---

## v0.0.1–v0.0.5 (Development Pre-releases)

| Version | Date | Key Changes |
|---------|------|-------------|
| v0.0.5 | 2026-06 | Streamlit dashboard, API endpoints |
| v0.0.4 | 2026-06 | Model training pipeline, digital twin |
| v0.0.3 | 2026-05 | Docker compose, RAG pipeline |
| v0.0.2 | 2026-05 | Forecasting models, risk engine |
| v0.0.1 | 2026-05 | Project scaffold, synthetic data generation |

---

## Future (Planned)

| Version | Target | Features |
|---------|--------|----------|
| v0.2.0 | Q3 2026 | Real data ingestion, LLM integration |
| v0.3.0 | Q4 2026 | Authentication, production hardening |
| v1.0.0 | TBD | Production release |
