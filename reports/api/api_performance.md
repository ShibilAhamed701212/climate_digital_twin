# API Performance

> **⚠️ Benchmarks on synthetic data with no load. Not representative of production.**

---

## Latency (Single Request, No Load)

| Endpoint | Avg Latency | P95 | P99 | Notes |
|----------|-------------|-----|-----|-------|
| `/health` (all) | ~5ms | ~10ms | ~20ms | Simple OK response |
| `/predict` | ~200–500ms | ~800ms | ~1.5s | Includes model load |
| `/risk/heat` | ~50ms | ~80ms | ~150ms | Stateless computation |
| `/risk/flood` | ~50ms | ~80ms | ~150ms | Stateless computation |
| `/risk/drought` | ~50ms | ~80ms | ~150ms | Stateless computation |
| `/risk/composite` | ~80ms | ~120ms | ~200ms | Aggregates 3 modules |
| `/scenario/run` | ~500ms–2s | ~3s | ~5s | Includes risk computation |
| `/twin/state` | ~20ms | ~40ms | ~80ms | Parquet read |
| `/rag/query` | ~10ms | ~20ms | ~50ms | FAISS search |
| `/copilot/ask` | ~50ms | ~80ms | ~150ms | Mock response (no LLM) |
| `/explain/risk` | ~30ms | ~50ms | ~100ms | Synthetic SHAP |

---

## Throughput (Not Tested)

| Metric | Value | Notes |
|--------|-------|-------|
| Max concurrent users | **Not tested** | Single-user demo only |
| Requests per second | **Not tested** | No load testing performed |
| Max memory under load | **Not tested** | No stress testing performed |
| Connection pooling | **Not tested** | No concurrent request testing |

---

## Response Sizes

| Endpoint | Avg Size | Max Size |
|----------|----------|----------|
| `/predict` | ~2 KB | ~10 KB (7-day forecast) |
| `/risk/*` | ~500 B | ~1 KB |
| `/scenario/run` | ~5 KB | ~50 KB (all districts) |
| `/rag/query` | ~3 KB | ~10 KB (5 chunks) |
| `/copilot/ask` | ~500 B | ~1 KB |

---

## Timeouts

| Service | Timeout | Behavior |
|---------|---------|----------|
| Forecasting API | 30s | Returns 504 on timeout |
| Scenario Engine | 30s | Returns 504 on timeout |
| All others | 10s | Returns 504 on timeout |

---

## Recommendations

1. **Performance testing is needed** before any production use
2. **Model caching** would reduce /predict latency (currently loads model per request)
3. **Connection pooling** for database/vector store
4. **Response compression** for large scenario responses
5. **Async endpoints** for long-running operations
6. **Proper load testing** with realistic request patterns
