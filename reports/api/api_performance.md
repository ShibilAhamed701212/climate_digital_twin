# API Performance Report — Climate Digital Twin

## 1. Expected Latency Based on Model Benchmarks

### Forecast Engine (`/forecast/predict`)

| Model | Inference Time (total) | Per Batch (64) | Startup Overhead |
|---|---|---|---|
| Transformer | **26.8 ms** | 2.6 ms | ~1-2s (model load) |
| LSTM | **701.5 ms** | 5.4 ms | ~1-2s (model load) |
| Baseline (MLP) | **1,849.5 ms** | 4.4 ms | <1s (small model) |
| PatchTST | 6.5 ms | 6.1 ms | Stub (untrained) |
| TimeMixer | 6.6 ms | 1.1 ms | Stub (untrained) |
| iTransformer | 3.2 ms | 2.7 ms | Stub (untrained) |

**Default model:** Transformer (fastest trained model, 69× faster than baseline).

**Expected `POST /forecast/predict` latency:**
- Transformer: ~50-100 ms (including deserialization, physics validation, response serialization)
- LSTM: ~750-800 ms
- Baseline: ~1,900 ms

### Scenario Engine (`/scenarios/simulate`)

| Operation | Expected Latency | Constraint |
|---|---|---|
| Single location, simple scenario | <100 ms | Deterministic engine |
| Multiple locations, combined scenario | <3,000 ms | Hard limit from `scenario.yaml` |
| Scenario creation | <50 ms | In-memory operation |
| Scenario listing | <10 ms | Cached preset list |

### Risk Engine (`/risk/assess`)

| Operation | Expected Latency | Notes |
|---|---|---|
| Single risk type assessment | <50 ms | Weighted scoring only |
| Full risk assessment (all 4 types) | <100 ms | No actual SHAP model calls (deterministic fallback) |
| SHAP explanation generation | <20 ms | Deterministic estimation, no actual model |
| Risk report generation | <200 ms | JSON + Markdown file I/O |

### RAG Service (`/search`)

| Operation | Expected Latency | Notes |
|---|---|---|
| Semantic search (top_k=3) | 50-200 ms | FAISS IndexFlatIP search is O(n) |
| Semantic search (top_k=10) | 50-350 ms | Depends on index size |
| Document indexing | 100-500 ms/doc | Embedding generation dominates |
| Index with sentence-transformers | 200-1000 ms | Real embeddings (vs dummy fallback) |

**FAISS index:** 30 chunks, 384-dim → search time is negligible (<5 ms for brute-force).

### Copilot Agent (`/ask`)

| Operation | Expected Latency | Performance Target |
|---|---|---|
| Simple query (greeting, twin state) | 500-2,000 ms | 2,000 ms |
| Forecast query | 1,000-5,000 ms | 5,000 ms |
| Scenario simulation | 2,000-8,000 ms | 8,000 ms |
| Risk assessment | 1,000-5,000 ms | 5,000 ms |
| Report generation (3 steps) | 3,000-10,000 ms | 10,000 ms |

Latency breakdown for a forecast query:
1. Intent classification: <50 ms (pattern matching)
2. Planning: <10 ms (pre-built plan templates)
3. Tool execution (forecast): ~100 ms
4. Response generation: <50 ms (template-based)
5. Memory storage: <10 ms
**Total:** ~200 ms (excluding LLM if enabled)

## 2. Health Check Endpoints

All 6 API services expose `GET /health` endpoints with sub-5ms response times.

| Service | Path | Expected Latency | Typical Response |
|---|---|---|---|
| API Gateway | `GET /health` | <2 ms | `{"status":"healthy","service":"fastapi-gateway","version":"1.0.0"}` |
| Twin State Manager | `GET /health` | <2 ms | Same pattern |
| Scenario Engine | `GET /health` | <2 ms | Same pattern |
| Risk Engine | `GET /health` | <2 ms | Same pattern |
| RAG Service | `GET /health` | <2 ms | Same pattern |
| Forecast Engine | `GET /health` | <2 ms | Same pattern |
| Copilot Agent | `GET /health` | **50-500 ms** | Includes Ollama health check + tool registry check |

The Copilot health endpoint is slower because it pings the Ollama service and checks all 6 registered tools.

### Monitoring Health Checks

Docker Compose health checks run every 10s (30s for Ollama) with 5s timeout and 3 retries.

## 3. Error Handling Patterns

### Common Error Responses

All services follow a consistent error pattern:

**404 Not Found:**
```json
{
  "detail": "No current state found for location 'KA-XXX-999'"
}
```

**422 Validation Error:**
```json
{
  "detail": "Invalid coordinates: longitude out of range"
}
```

**500 Internal Error:**
```json
{
  "detail": "Search service unavailable: FAISS index not initialized"
}
```

### Error Patterns by Service

| Service | Error Type | Pattern |
|---|---|---|
| Twin State Manager | `ValueError` → 422 | Coordinate bounds, validation |
| Twin State Manager | `RuntimeError` → 500 | Engine not initialized |
| Scenario Engine | `ValueError` → 404 | Scenario not found |
| Risk Engine | — | No explicit error handling |
| RAG Service | `Exception` → 500 | Search failures |
| Forecast Engine | `PredictionError` → 500 | Model inference failures |
| Copilot Agent | Tool errors → 400 | LLM/query failures |

### Retry Strategy

Docker Compose health checks implement:
- **Interval:** 10s (30s for Ollama)
- **Timeout:** 5s (10s for Ollama)
- **Retries:** 3 (5 for Ollama)
- **Start period:** 60s for Ollama (longer model download time)

## 4. Inference Pipeline Latency

### Forecast Inference (`backend/services/forecast/inference.py`)

```
Request → Data Loading → Model Inference → Inverse Scaling → Physics Validation → CI Computation → Response
  <1ms         ~10ms          ~27ms              ~1ms             <1ms              <1ms          <1ms
```

### Copilot Orchestration (`copilot/workflows/orchestrator.py`)

```
Request → Intent Classify → Plan → Execute → Generate → Memorize → Response
  <1ms        ~5ms          <1ms   ~varies   ~10ms      <5ms      <1ms
```

Execution time varies by intent (forecast: ~100ms, report: ~300ms, scenario: ~500ms).

## 5. Synthetic vs Real Data Performance

| Component | Real Data | Synthetic Fallback | Difference |
|---|---|---|---|
| Model inference | ~27ms (Transformer) | ~5ms (random tensor) | Real is 5× slower |
| Embedding generation | 100-1000ms (sentence-transformers) | ~1ms (dummy hash) | Real is 100-1000× slower |
| SHAP explanation | ~500ms (KernelExplainer) | ~1ms (deterministic estimation) | Real is 500× slower |
| NASA POWER download | 10-60s (network I/O) | ~500ms (synthetic grid gen) | Real is 20-120× slower |

## 6. Performance Bottlenecks

| Bottleneck | Severity | Mitigation |
|---|---|---|
| LLM model loading (Ollama) | High | Warm up with startup script |
| Sentence-transformers on first call | High | Pre-load in Docker HEALTHCHECK |
| Torch model weight loading | Medium | Cache in memory after first request |
| FAISS index rebuild on delete | Low | Rebuilds entire index (30 chunks only) |
| Python GIL in Streamlit | Medium | Uvicorn multi-worker for API services |
| DuckDB on large state history | Low | Per-location Parquet files |

## 7. Scaling Recommendations

| Service | Scaling Strategy | Expected Throughput |
|---|---|---|
| API Gateway | Horizontally scale stateless instances | 10,000+ req/s |
| Twin State Manager | Vertical (DuckDB single-writer) | 1,000 req/s |
| Forecast Engine | Scale with model servers; GPU for batch | 100 req/s per GPU |
| Risk Engine | Stateless, can scale horizontally | 5,000 req/s |
| RAG Service | FAISS in-memory, scale read replicas | 1,000 req/s |
| Copilot Agent | LLM is bottleneck; scale with Ollama instances | 10-50 req/s per GPU |
| Streamlit Dashboard | Session-locked; consider Nginx load balancing | 100 concurrent users |
