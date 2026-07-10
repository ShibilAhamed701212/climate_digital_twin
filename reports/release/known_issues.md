# Known Issues — Climate Digital Twin v1.0.0

**Last updated:** 2026-06-29
**Total known issues:** 18 test failures + 5 system limitations

---

## 1. Known Test Failures (18 Total)

All 18 failures are **environment-related dependency version mismatches** — they do not occur inside Docker containers. Source: `docs/KNOWN_FAILURES.md`.

### Group A — NumPy 2.x / SciPy Compatibility (1 failure)

| ID | Test | Root Cause |
|---|---|---|
| A1 | `TestCharts::test_scatter_plot` | NumPy 2.x removed `np.long`. SciPy (via plotly/statsmodels) still references it. |

**Impact:** Dashboard scatter plot charts fail outside Docker.

### Group B — Streamlit / Starlette API Breakage (1 failure)

| ID | Test | Root Cause |
|---|---|---|
| B1 | `TestComponents::test_entity_detail_table_all_fields` | Streamlit version depends on Starlette version that removed `DEFAULT_EXCLUDED_CONTENT_TYPES`. |

**Impact:** Dashboard component rendering fails outside Docker.

### Group C — NumPy 2.x `_core` Module Removed (16 failures)

| ID | Test File | Tests |
|---|---|---|
| C1-C6 | `tests/unit/test_rag_api.py` | `test_index_and_search`, `test_delete_document`, `test_list_sources`, `test_get_index_stats`, `test_retrieve_context`, `test_rebuild_index` |
| C7-C9 | `tests/unit/test_rag_pipeline.py` | `test_index_markdown_file`, `test_index_text_file`, `test_index_directory` |
| C10-C12 | `tests/unit/test_rag_retriever.py` | `test_retrieve_context_with_data`, `test_metadata_filter`, `test_score_threshold` |
| C13-C16 | `tests/unit/test_rag_vector_store.py` | `test_add_and_search`, `test_delete_document`, `test_clear`, `test_list_sources` |

**Root cause:** FAISS (built for NumPy 2.x) tries to `from numpy._core._multiarray_umath import __cpu_features__`. NumPy 1.26.0 does not have `_core` (restructured in 2.x).

**Impact:** All RAG/FAISS functionality fails on local Python environments without Docker.

### How to Use This Baseline

```text
New failures introduced:   (should be 0)
Known failures remaining:  (should match this document — 18 as of 2026-06-29)
```

If a **new** failure appears in the test suite, it must be investigated as a potential regression. If a **known** failure starts passing, update this document.

---

## 2. System Limitations

### L1 — RAG Service Unavailable Outside Docker

| Field | Value |
|---|---|
| **Issue** | FAISS/numpy version conflict prevents local RAG service operation |
| **Impact** | RAG service falls back to synthetic data (deterministic hash-based dummy embeddings) |
| **Workaround** | Always run services via `docker compose up` |
| **Severity** | Medium |
| **Resolution** | Deploy via Docker (all environments consistent) |

### L2 — Training Data Limited to 2011

| Field | Value |
|---|---|
| **Issue** | `data_config.yaml` specifies date range 1981-01-01 to 2023-12-31, but actual processed training data covers only 2011-2023 due to synthetic data generation constraints |
| **Impact** | Models trained on reduced temporal range (~12 years vs 43 years) |
| **Workaround** | Re-run pipeline with NASA POWER API for full historical range |
| **Severity** | Low (POC system) |
| **Resolution** | Sprint 7 (Data Pipeline V2) |

### L3 — Grid Bounds Minor Offset

| Field | Value |
|---|---|
| **Issue** | Code uses `max_lon=79.0` but documentation specifies `max_lon=78.5` |
| **Impact** | Minor coordinate shift in grid generation (~0.5° eastward) |
| **Workaround** | None needed — within acceptable tolerance for POC |
| **Severity** | Low |
| **Resolution** | Document and fix in next sprint |

### L4 — No Authentication on Any API Endpoint

| Field | Value |
|---|---|
| **Issue** | All 32 API endpoints have zero authentication (no API keys, JWT, cookies) |
| **Impact** | Any service reachable on the network can access all endpoints |
| **Workaround** | Run only in isolated/trusted networks (hackathon LAN) |
| **Severity** | Critical for production; acceptable for POC |
| **Resolution** | Sprint 8 (Security Hardening) |

### L5 — No PDF Loader for RAG Knowledge Base

| Field | Value |
|---|---|
| **Issue** | `DocumentFormat.PDF` is declared in the enum but no PDF loader is registered in `LoaderFactory` |
| **Impact** | Cannot index PDF documents into the knowledge base |
| **Workaround** | Convert PDFs to Markdown before indexing |
| **Severity** | Medium |
| **Resolution** | Sprint 8 (RAG Enhancement) |

---

## 3. Dependency Constraints

| Dependency | Version | Issue | Workaround |
|---|---|---|---|
| `numpy` | ≥1.24 | FAISS requires numpy <2 for local dev | Use Docker |
| `faiss-cpu` | ≥1.7 | Built for numpy 2.x, incompatible with 1.26 | Use Docker |
| `streamlit` | ≥1.28 | Starlette version mismatch | Use Docker |
| `torch` | ≥2.0 | Large download (~2 GB) | Included in Docker image |
| `ollama/ollama` | latest | First pull of Qwen3:8b is ~4.7 GB | Auto-downloaded by Docker |

---

## 4. Operational Notes

### Port Conflicts

If any of the default ports (8000-8006, 8501, 11434, 9090, 3000) are occupied on the host:

```bash
# Edit .env
TWIN_STATE_MGR_PORT=8101
FORECAST_PORT=8106
# ... etc
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### Docker Resource Requirements

| Resource | Estimated Need |
|---|---|
| Disk space | ~10 GB (images + volumes + Ollama model) |
| RAM | ~4 GB minimum (Ollama ~2 GB, Python services ~2 GB) |
| CPU | 2+ cores recommended |

### Ollama Reachability

The Copilot agent connects to Ollama via Docker internal networking (`http://ollama:11434`). If running services without Docker, set:

```bash
# In .env or environment
OLLAMA_HOST=http://localhost:11434
```

### First-Pull Timeout

Ollama's first model download can exceed the 60-second `start_period`. If the copilot-agent health check fails initially:

```bash
# Check Ollama status
docker compose logs ollama

# Wait for model download to complete (watch logs)
docker compose logs -f ollama
```

---

## 5. Resolution Roadmap

| Issue | Target Sprint | Fix |
|---|---|---|
| A1, B1, C1-C16 | Sprint 6 (Deployment Hardening) | Pin dependency versions in Dockerfiles |
| L1 (RAG outside Docker) | Sprint 6 | Containerize dev environment |
| L2 (Training data 2011 only) | Sprint 7 (Data V2) | Integrate NASA POWER API for full range |
| L3 (Grid bounds offset) | Sprint 7 | Fix lon=78.5 consistency |
| L4 (No auth) | Sprint 8 (Security) | API key middleware |
| L5 (No PDF loader) | Sprint 8 (RAG) | Implement PyMuPDF loader |

---

## 6. Test Exclusion Policy

The following test categories must **always** pass and are excluded from the known failures baseline:

- All tests in `tests/unit/test_physics.py`
- All tests in `tests/unit/test_predictor.py`
- All tests in `tests/unit/test_evaluator.py`
- All integration tests (`tests/integration/`)
- All data pipeline tests (download, clean, validate, features, export)
- All scenario engine tests
- All risk engine tests
- All digital twin tests
- All trainer/model architecture tests
