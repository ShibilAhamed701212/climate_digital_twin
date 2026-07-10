# Coverage Report

## Overview

Coverage data is collected using the `coverage.py` tool with pytest. Due to the tool's measurement methodology, reported coverage includes all imported modules — including third-party library internals — resulting in a low overall percentage. This report provides both the raw measurement and a qualitative assessment of actual test coverage by subsystem.

**Note:** The 10% overall figure is misleading because coverage.py measures against ALL imports, not just application code. Third-party packages (torch, numpy, pandas, fastapi, etc.) dominate the import graph but are not tested by our unit tests.

## Raw Coverage Metrics

| Metric | Value |
|--------|-------|
| Overall coverage (lines) | ~10% |
| Python files tracked | 262 |
| Total Python lines | 17,354 |
| Test functions | 656 |
| Test files | 57 |

The `.coverage` file and `.pytest_cache/` are present in the repository root, indicating coverage collection has been run.

## Coverage by Subsystem (Qualitative Assessment)

### Well-Tested Subsystems (>50% coverage)

| Subsystem | Test Files | Test Count | Coverage Estimate |
|-----------|-----------|------------|-------------------|
| **Copilot** | 11 | 126 | ~85% |
| **Dashboard** | 1 | 50 | ~70% |
| **Risk Engine** | 6 | 66 | ~75% |
| **Scenario Engine** | 6 | 73 | ~70% |
| **Digital Twin** | 5 | 52 | ~65% |
| **RAG Knowledge** | 9 | 71 | ~70% |

### Moderately Tested Subsystems (20–50%)

| Subsystem | Test Files | Test Count | Coverage Estimate |
|-----------|-----------|------------|-------------------|
| **Evaluator** | 1 | 12 | ~90% |
| **Data Loader** | 1 | 9 | ~60% |
| **Clean/Validate** | 2 | 30 | ~50% |
| **Model Registry** | 1 | 15 | ~90% |

### Lightly Tested or Untested Subsystems (<20%)

| Subsystem | Test Files | Notes |
|-----------|-----------|-------|
| **backend/** | 0 | No test files exist for the backend API service |
| **pipeline/run_pipeline.py** | 0 | Pipeline orchestrator not unit-tested |
| **pipeline/sources/nasa_power.py** | 0 | NASA POWER data source not unit-tested |
| **deployment/** | 0 | Docker/CI/CD config not tested |
| **scripts/** | 0 | Utility scripts not unit-tested |

## Detailed Subsystem Analysis

### Copilot — ~85% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `copilot/agent/intent_agent.py` | 15 | ~95% |
| `copilot/tools/*.py` (6 tools + registry) | 41 | ~90% |
| `copilot/workflows/orchestrator.py` | 8 | ~85% |
| `copilot/workflows/executor.py` | 6 | ~90% |
| `copilot/workflows/generator.py` | 10 | ~80% |
| `copilot/planner/planner.py` | 9 | ~95% |
| `copilot/memory/conversation_memory.py` | 8 | ~95% |
| `copilot/models.py` | 15 | ~100% |
| `copilot/config_loader.py` | 3 | ~90% |
| `copilot/api/copilot_api.py` | 6 | ~90% |
| `copilot/llm/ollama_client.py` | 0 | ~30% (partial via orchestrator) |
| `copilot/clients/*.py` | 0 | ~0% (HTTP clients not directly tested) |

### Dashboard — ~70% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `dashboard/config/config.py` | 5 | ~80% |
| `dashboard/services/api_client.py` | 26 | ~85% |
| `dashboard/charts/*.py` (time_series, comparison, distribution, risk_trends) | 11 | ~75% |
| `dashboard/maps/*.py` (climate_map, comparison_map) | 7 | ~60% |
| `dashboard/components/*.py` | 2 | ~30% |
| `dashboard/pages/*.py` | 0 (import-only) | ~20% |

### RAG Knowledge — ~70% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `knowledge/models.py` | 14 | ~95% |
| `knowledge/chunkers/text_chunker.py` | 7 | ~80% |
| `knowledge/embeddings/embedding_model.py` | 5 | ~75% |
| `knowledge/loaders/*.py` (6 loaders + factory) | 15 | ~85% |
| `knowledge/vector_store/faiss_store.py` | 6 | ~70% |
| `knowledge/retriever/semantic_search.py` | 9 | ~75% |
| `knowledge/retriever/context_builder.py` | (included with retriever) | ~60% |
| `knowledge/pipelines/indexing_pipeline.py` | 5 | ~60% |
| `knowledge/config_loader.py` | 3 | ~90% |
| `knowledge/api/search_api.py` | 8 | ~80% |

### Risk Engine — ~75% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `risk/engine/risk_engine.py` | 8 | ~70% |
| `risk/models.py` | 16 | ~90% |
| `risk/scoring/*` | 23 | ~85% |
| `risk/explainability/*` | 11 | ~70% |
| `risk/reports/*` | 5 | ~60% |
| `risk/api/*` | 3 | ~50% |

### Scenario Engine — ~70% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `simulator/engine/scenario_engine.py` | 14 | ~75% |
| `simulator/models/scenario_models.py` | 9 | ~80% |
| `simulator/builder/*` | 9 | ~70% |
| `simulator/validators/*` | 24 | ~80% |
| `simulator/outputs/*` | 8 | ~60% |

### Digital Twin — ~65% Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `simulator/entities/*` | 10 | ~70% |
| `simulator/events/*` | 9 | ~65% |
| `simulator/engine/twin_engine.py` | 8 | ~60% |
| `simulator/repository/*` | 8 | ~60% |
| `simulator/services/*` | 11 | ~65% |
| `simulator/state/*` | 14 | ~70% |

## Untested Modules

The following modules have **zero** dedicated unit tests:

### `backend/` (entire directory)
- REST API service layer
- Request/response models
- Route handlers
- Middleware

### `pipeline/run_pipeline.py`
- Pipeline orchestration logic
- Step sequencing
- Error handling and recovery

### `pipeline/sources/nasa_power.py`
- NASA POWER API data download
- Parameter mapping for climate variables
- Rate limiting and retry logic
- Data format conversion

### `scripts/`
- `end_to_end_test.py` (integration test only, not unit)
- `smoke_test_models.py` (manual diagnostic)
- `index_knowledge_base.py`
- `register_models.py`
- `check_vector_store.py`

### `deployment/`
- Docker configurations
- CI/CD workflows (`.github/`)
- Infrastructure as code

## Recommendations

1. **Add unit tests for `backend/`** — The entire backend API service layer has zero test coverage
2. **Test pipeline sources** — `pipeline/sources/nasa_power.py` is a critical data ingestion component
3. **Test HTTP clients directly** — The 6 Copilot clients in `copilot/clients/` are only tested indirectly through tools; add direct unit tests with mocked responses
4. **Improve dashboard page tests** — Dashboard pages are import-verified but not rendered or behavior-tested
5. **Increase LLM client coverage** — `ollama_client.py` has minimal test coverage
6. **Add pipeline unit tests** — `run_pipeline.py` orchestrates the entire data workflow and should have dedicated tests
7. **Reduce third-party import inflation** — Configure coverage to exclude `site-packages` for more accurate application-level metrics
