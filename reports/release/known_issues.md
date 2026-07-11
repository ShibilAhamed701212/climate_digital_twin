# Known Issues

> **Current issues as of v0.1.0 (hackathon proof-of-concept).**

---

## Critical Issues

| # | Issue | Component | Impact | Workaround |
|---|-------|-----------|--------|------------|
| 1 | **All data is synthetic** | Data pipeline | No real-world validation possible | Cannot be worked around — needs real data ingestion |
| 2 | **Copilot returns mock responses** | Copilot | No real AI assistance | None — LLM not wired |
| 3 | **FAISS index starts empty** | RAG | No knowledge retrieval on first use | Call `/index` endpoint explicitly |
| 4 | **No authentication** | All services | Open access | Acceptable for demo only |

---

## Test Issues

| # | Issue | Tests Affected | Root Cause | Status |
|---|-------|---------------|------------|--------|
| 5–22 | 18 test failures in certain environments | Dashboard tests | NumPy/FAISS/Streamlit version mismatches | ⚠️ Pre-existing |
| 23 | No model tests | 0 | Not implemented | ⚠️ Known gap |
| 24 | No API tests | 0 | Not implemented | ⚠️ Known gap |

---

## Dashboard Issues

| # | Issue | Page | Impact | Status |
|---|-------|------|--------|--------|
| 25 | Knowledge Base page (08) is mock | 08_Knowledge.py | No content | ⚠️ Mock |
| 26 | Feedback page (09) is mock | 09_Feedback.py | No functionality | ⚠️ Mock |
| 27 | BHAI State page (10) is mock | 10_BHAI_State.py | Placeholder content | ⚠️ Mock |
| 28 | Charts flash on data refresh | All | Visual glitch | ⚠️ Minor |

---

## Model Issues

| # | Issue | Model | Impact | Status |
|---|-------|-------|--------|--------|
| 29 | PatchTST is a stub | PatchTST | Cannot be used | ⚠️ Not implemented |
| 30 | TimeMixer is a stub | TimeMixer | Cannot be used | ⚠️ Not implemented |
| 31 | iTransformer is a stub | iTransformer | Cannot be used | ⚠️ Not implemented |
| 32 | Ensemble not trained | Ensemble | Predictions are random | ⚠️ Mock |
| 33 | All models R²=0.87 (suspicious) | All | Indicates overly simple synthetic data | ⚠️ Known |

---

## Deployment Issues

| # | Issue | Component | Impact | Status |
|---|-------|-----------|--------|--------|
| 34 | Ollama model pull required | Ollama | 8GB download on first run | ⚠️ Manual step |
| 35 | Docker images >1GB each | All services | Large disk usage | ⚠️ Needs optimization |
| 36 | Streamlit hot-reload broken | Dashboard | Code changes require rebuild | ⚠️ Known |

---

## API Issues

| # | Issue | Endpoint | Impact | Status |
|---|-------|----------|--------|--------|
| 37 | All responses based on synthetic data | All | No real climate data returned | ⚠️ Known |
| 38 | No request validation errors | All | Invalid requests silently handled | ⚠️ Needs improvement |

---

## Documentation Issues

| # | Issue | Impact | Status |
|---|-------|--------|--------|
| 39 | Previous reports had inflated claims (656 tests, 95% readiness, etc.) | Misleading | ✅ Being corrected (this update) |
| 40 | No architecture decision records | Knowledge loss | ⚠️ Missing |
| 41 | No API client SDK docs | Integration friction | ⚠️ Missing |
