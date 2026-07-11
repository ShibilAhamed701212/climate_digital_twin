# Performance Report

> **⚠️ Performance measured on synthetic data with no load testing.** Metrics reflect demo conditions only.

---

## Inference Latency (Synthetic Data, CPU)

| Operation | Latency | Notes |
|-----------|---------|-------|
| MLP prediction (batch=32) | ~12ms | Small model, synthetic input |
| LSTM prediction (batch=32) | ~15ms | Medium model, synthetic input |
| Transformer prediction (batch=32) | ~14ms | Largest model, synthetic input |
| Single sample (any model) | ~3–4ms | No batching overhead |

---

## Memory Footprint

| Component | Memory | Notes |
|-----------|--------|-------|
| Forecasting API (loaded) | ~200–400 MB | Model weights + dependencies |
| FAISS index (loaded) | ~5 MB | 30 chunks, 384-dim |
| Streamlit dashboard | ~150–300 MB | Python + UI state |
| Docker per service | ~100–200 MB | Python runtime + dependencies |
| Total system (all containers) | ~2–4 GB | Estimated |

---

## Codebase Size

| Metric | Count | Notes |
|--------|-------|-------|
| Python files | ~262 | Includes tests, scripts, tools |
| Total LOC | ~17,354 | Rough count |
| Config files | ~10 | YAML + Python + JSON |
| Docker images | 8 | Built from Dockerfiles |
| Test files | ~30+ | Dashboard-focused |

---

## API Latency (No Load)

| Endpoint | Latency | Notes |
|----------|---------|-------|
| `/predict` | ~200–500ms | Includes model load + inference |
| `/risk/heat` | ~50ms | Stateless computation |
| `/risk/flood` | ~50ms | Stateless computation |
| `/risk/drought` | ~50ms | Stateless computation |
| `/scenario/run` | ~500ms–2s | Includes scenario + risk computation |
| `/copilot/ask` | ~50ms | Mock response (no LLM call) |
| `/rag/query` | ~10ms | FAISS search (small index) |
| `/health` | ~5ms | Simple OK response |

---

## Startup Time

| Service | Time | Notes |
|---------|------|-------|
| Forecasting API | ~5s | Model loading |
| Dashboard | ~10s | Streamlit init + API warmup |
| All services (compose) | ~30–60s | Sequential container startup |

---

## Load Testing

**Not performed.** No load testing, stress testing, or scalability analysis has been done. Metrics above are from single-user demo conditions on synthetic data.
