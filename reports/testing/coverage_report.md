# Coverage Report

> **⚠️ Coverage measured for dashboard tests only. Most subsystems have 0% coverage.**

---

## Coverage by Subsystem

| Subsystem | Files | Lines | Coverage | Status |
|-----------|-------|-------|----------|--------|
| Dashboard (`app/`) | ~20 | ~3,000 | ~60% | ✅ Partial |
| Digital Twin (`digital_twin/`) | ~5 | ~800 | ~30% | ⚠️ Low |
| Scenario Engine (`scenario_engine/`) | ~3 | ~500 | ~25% | ⚠️ Low |
| Risk Engine (`risk/`) | ~5 | ~600 | ~20% | ⚠️ Low |
| Forecasting Models (`models/`) | ~7 | ~2,000 | **0%** | ❌ None |
| Forecasting API (`api/`) | ~2 | ~300 | **0%** | ❌ None |
| RAG (`rag/`) | ~5 | ~600 | **0%** | ❌ None |
| Copilot (`copilot/`) | ~5 | ~500 | **0%** | ❌ None |
| Explainability (`explainability/`) | ~2 | ~200 | **0%** | ❌ None |
| Configuration (`config/`) | ~5 | ~300 | ~40% | ⚠️ Low |

---

## Untested Modules (Critical Gap)

The following production code has **zero test coverage**:

1. **All forecasting models** — MLP, LSTM, Transformer forward passes never tested
2. **All API endpoints** — No request/response validation tests
3. **FAISS indexing pipeline** — Build/search never tested
4. **Copilot intent classification** — Keyword matching never tested
5. **SHAP explainer** — Synthetic SHAP values never verified
6. **Data pipeline** — Download/validate/clean steps never tested with real data

---

## Coverage by Type

| Type | Coverage | Notes |
|------|----------|-------|
| Unit tests | Dashboard only | No model/API unit tests |
| Integration tests | Minimal | Pipeline stage coupling not tested |
| E2E tests | Pipeline flow | Synthetic data only |
| Performance tests | None | No load/stress tests |
| Security tests | None | No auth/input validation tests |

---

## Recommendations

| Priority | Action | Impact |
|----------|--------|--------|
| 🔴 Critical | Add model forward pass tests | Catches regression in core ML code |
| 🔴 Critical | Add API endpoint tests | Validates request/response contract |
| 🟡 High | Add FAISS index build/search tests | Validates RAG pipeline |
| 🟡 High | Add copilot intent tests | Validates classification accuracy |
| 🟢 Medium | Add risk engine unit tests | Validates scoring math |
| 🟢 Medium | Add scenario engine unit tests | Validates perturbation logic |
| ⚪ Low | Add configuration validation tests | Catches YAML parse errors |
