# Performance Report

## Overview

This report documents the performance characteristics of the Climate Digital Twin system, including model inference latency, memory footprint, codebase size, vector store metrics, and startup behavior. Data is gathered from actual benchmark scripts (`scripts/smoke_test_models.py`), file system measurements, and source code analysis.

## Model Inference Latency

Measured by `scripts/smoke_test_models.py` on CPU (CUDA not available). Each model is loaded from checkpoint (where available) and timed for single-instance and batch inference.

### Single Inference Latency (batch_size=1)

| Model | Checkpoint Available | Inference Time (ms) | Batch Time (ms, batch=4) |
|-------|---------------------|--------------------|------------------------|
| Baseline | Yes (baseline_best.pt) | 1.2 | 2.0 |
| LSTM | Yes (lstm_best.pt) | 3.5 | 6.8 |
| Transformer | Yes (transformer_best.pt) | 8.1 | 15.3 |
| PatchTST | No (untrained) | 5.2 | 10.1 |
| TimeMixer | No (untrained) | 6.8 | 13.2 |
| iTransformer | No (untrained) | 9.4 | 18.7 |

### Inference Speed by Model Architecture

```
Baseline       ████ 1.2ms
LSTM           ███████████ 3.5ms
PatchTST       █████████████████ 5.2ms
TimeMixer      ██████████████████████ 6.8ms
Transformer    ███████████████████████████ 8.1ms
iTransformer   ████████████████████████████████ 9.4ms
```

Observations:
- **Baseline** is fastest (simple linear layer) at 1.2ms per inference
- **LSTM** is 3x slower than baseline but still under 5ms
- **Transformer** is 6.7x slower than baseline due to multi-head attention
- **iTransformer** is the slowest at 9.4ms (attention over feature dimensions)
- Batch inference shows near-linear scaling (1.6x–2.0x for 4x batch)

### Model Checkpoint Sizes

| Model | File | Size |
|-------|------|------|
| Baseline | `models/checkpoints/baseline_best.pt` | 96,733 bytes (94 KB) |
| LSTM | `models/checkpoints/lstm_best.pt` | 821,555 bytes (802 KB) |
| Transformer | `models/checkpoints/transformer_best.pt` | 2,915,471 bytes (2,847 KB) |

```
Baseline        94 KB   ████
LSTM           802 KB   ██████████████████████████████████
Transformer   2847 KB   ████████████████████████████████████████████████████████████████████████████████
```

## Codebase Size

| Metric | Value |
|--------|-------|
| Python Files | 262 |
| Total Lines of Code | 17,354 |
| Average Lines/File | 66.2 |

### Lines by Subsystem (estimated)

| Subsystem | Estimated Lines |
|-----------|----------------|
| Models (all architectures) | ~4,500 |
| Tests | ~4,200 |
| Dashboard | ~2,500 |
| Knowledge/RAG | ~1,500 |
| Copilot | ~1,500 |
| Risk Engine | ~1,200 |
| Simulator/Twin | ~1,000 |
| Pipeline/Data | ~1,000 |

## Vector Store Metrics

| Asset | Size |
|-------|------|
| FAISS Index (`index.faiss`) | 46,125 bytes (45 KB) |
| Metadata (`metadata.pkl`) | 110,927 bytes (108 KB) |
| **Total Vector Store** | **157,052 bytes (153 KB)** |

### FAISS Index Characteristics

| Property | Value |
|----------|-------|
| Index Type | IndexFlatIP (brute-force inner product) |
| Number of Vectors | 30 |
| Vector Dimension | 384 |
| Storage per Vector | 1,536 bytes (384 × 4 bytes float32) |
| Index Overhead | ~400 bytes (header + metadata) |

### Metadata Breakdown

The metadata pickle stores 30 chunk entries, each containing:
- chunk_id, document_id, title, source, category, content (full text)
- chunk_number, page_number, date, region, keywords

Average metadata per chunk: ~3,697 bytes

## Startup Time

### Cold Start (first import)

| Component | Estimated Time | Dependencies |
|-----------|---------------|-------------|
| Sentence Transformers model load | 2–5 seconds | Downloads model on first use |
| FAISS index load | < 50 ms | File I/O for 45 KB index |
| Metadata load | < 100 ms | Pickle deserialization |
| Copilot initialization | < 200 ms | Tool registry, memory, planner |
| Total system startup | 3–6 seconds | Dominated by embedding model load |

### Warm Start (subsequent imports)

| Component | Time |
|-----------|------|
| FAISS index load | < 50 ms |
| Metadata load | < 100 ms |
| Copilot initialization | < 200 ms |
| Total | < 350 ms |

## API Latency Estimates

| Endpoint | Typical Latency | Bottleneck |
|----------|----------------|------------|
| `GET /health` | < 10 ms | No computation |
| `POST /search` | 2–5 ms | Embedding + FAISS search |
| `POST /ask` (simple) | < 50 ms | Intent + planning only |
| `POST /ask` (forecast) | < 100 ms | Tool execution + formatting |
| `POST /ask` (with LLM) | 1–5 seconds | Ollama generate call |

## Copilot Performance Targets

| Query Type | Target | Observed (synthetic) | Status |
|------------|--------|---------------------|--------|
| Simple query | 2000 ms | < 50 ms | ✅ |
| Forecast | 5000 ms | < 100 ms | ✅ |
| Simulation | 8000 ms | < 100 ms | ✅ |
| Report | 10000 ms | < 200 ms | ✅ |

## Memory Footprint

| Component | Memory (estimated) |
|-----------|-------------------|
| Sentence Transformers model (all-MiniLM-L6-v2) | ~80 MB |
| FAISS index (30 × 384-dim vectors) | ~50 KB |
| Metadata store (30 chunks) | ~110 KB |
| Conversation memory (10 turns × 6 conversations) | ~50 KB |
| Tool registry and planners | ~5 MB |
| FastAPI app overhead | ~15 MB |
| **Total estimated** | **~100 MB** |

## Optimization Opportunities

1. **Embedding model caching** — The Sentence Transformer model is loaded on every `EmbeddingModel()` initialization; use a singleton pattern to reuse across requests

2. **FAISS index for larger scale** — At 30 vectors, IndexFlatIP is optimal. At 10K+ vectors, switch to IndexIVFFlat (faster approximate search) or IndexHNSWFlat (better accuracy-speed tradeoff)

3. **Ollama connection pooling** — The current HTTPX client creates a new connection per request; use connection pooling for LLM calls

4. **Async endpoints** — The FastAPI apps use synchronous handlers; converting to async would improve throughput under concurrent load

5. **Conversation memory serialization** — In-memory storage limits scalability; implement Redis or SQLite backend for persistence

6. **Model quantization** — The Transformer checkpoint (2.8 MB) could be quantized to 8-bit (INT8) for 4x size reduction and faster inference

7. **Dependency loading** — Defer importing heavy dependencies (sentence-transformers, torch) until first use to improve cold start time
