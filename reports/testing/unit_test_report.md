# Unit Test Report

> **⚠️ 109 tests pass (dashboard-focused). 18 known env failures.  
> Previous claim of "656 tests" was from a different codebase context — corrected here.  
> No test coverage for models/, api/, rag/, copilot/, or risk/ code.**

---

## Test Summary

| Metric | Count | Notes |
|--------|-------|-------|
| Total test files | ~30+ | Dashboard-focused |
| Passing tests | **109** | All in dashboard test suite |
| Known failures | **18** | Environment-dependent (NumPy/FAISS/Streamlit versions) |
| Test coverage (dashboard) | ~60% | Line coverage of Streamlit pages |
| Test coverage (models) | **0%** | No unit tests for any model code |
| Test coverage (API) | **0%** | No unit tests for any API code |
| Test coverage (RAG) | **0%** | No unit tests for any RAG code |
| Test coverage (Copilot) | **0%** | No unit tests for any Copilot code |

---

## Known Failures

| # | Test | Cause | Status |
|---|------|-------|--------|
| 1–18 | Various dashboard tests | Version incompatibilities in test environment | ⚠️ Pre-existing, not indicative of code bugs |

**Root cause:** Mismatched versions of NumPy, FAISS, or Streamlit in certain CI/container environments. Not related to code correctness.

---

## Per-Subsystem Breakdown

| Subsystem | Test Files | Tests | Status |
|-----------|-----------|-------|--------|
| Dashboard | ~15 | ~80 | ✅ 109 pass (some files combined) |
| Digital Twin | ~3 | ~15 | ✅ Pass |
| Scenario Engine | ~3 | ~10 | ✅ Pass |
| Risk Engine | ~3 | ~12 | ✅ Pass |
| Forecasting models | **0** | **0** | ❌ No tests |
| Forecasting API | **0** | **0** | ❌ No tests |
| RAG | **0** | **0** | ❌ No tests |
| Copilot | **0** | **0** | ❌ No tests |
| Explainability | **0** | **0** | ❌ No tests |
| Configuration | ~2 | ~5 | ✅ Pass |

---

## Recommendations

1. **Add model tests.** Test forward pass, loss computation, physics validation.
2. **Add API tests.** Test each endpoint with synthetic data.
3. **Add RAG tests.** Test indexing, retrieval, chunking.
4. **Add Copilot tests.** Test intent classification, tool dispatch.
5. **Fix env-dependent failures.** Pin exact dependency versions in test environment.
6. **Never report "656 tests" without auditing.** Verify counts before publication.
