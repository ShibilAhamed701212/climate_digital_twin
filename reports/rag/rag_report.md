# RAG Report

> **⚠️ FAISS index starts EMPTY. Must be populated on first run.  
> `generate_answer()` is a MOCK — returns template responses, not LLM-generated answers.  
> Total corpus: 15 documents → ~30 chunks (tiny demo).**

---

## Architecture

```
Document Loading
    │
    ├── MD Loader     → .md files (working)
    ├── TXT Loader    → .txt files (working)
    ├── CSV Loader    → .csv files (working)
    ├── JSON Loader   → .json files (working)
    └── PDF Loader    → ⚠️ STUB — no actual PDF parsing
    │
    ▼
RecursiveChunker (chunk_size=700, overlap=120)
    │
    ▼
Embedding → sentence-transformers all-MiniLM-L6-v2 (384-dim)
    │
    ▼
FAISS IndexFlatIP (cosine similarity via inner product on normalized vectors)
    │
    ▼
Retrieval → top_k=5, threshold=0.5
    │
    ▼
generate_answer() → ⚠️ MOCK — returns template response
```

---

## Vector Store

| Property | Value |
|----------|-------|
| Index type | IndexFlatIP (inner product) |
| Dimensionality | 384 |
| Embedding model | all-MiniLM-L6-v2 |
| Default state | **EMPTY** — no documents pre-loaded |
| Indexed documents | 15 (when populated) |
| Total chunks | ~30 (when populated) |

---

## Document Corpus

15 documents in `data/documents/` across 5 categories:

| Category | Count | Examples |
|----------|-------|----------|
| Government | 3 | Policy documents |
| ISRO | 3 | Space agency reports |
| IMD | 3 | Meteorological reports |
| Research | 3 | Academic papers |
| Risk | 3 | Risk assessment guides |

---

## Chunking Strategy

| Parameter | Value |
|-----------|-------|
| Chunk size | 700 characters |
| Overlap | 120 characters |
| Strategy | Recursive split on headers/paragraphs |

---

## Retrieval Configuration

| Parameter | Value |
|-----------|-------|
| Top-K | 5 |
| Similarity threshold | 0.5 |
| Search type | Similarity (no MMR) |
| Return format | JSON with text + metadata + score |

---

## API Endpoints

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/query` | POST | Retrieve relevant chunks | ✅ Working (on populated index) |
| `/index` | POST | Index documents | ✅ Working |
| `/health` | GET | Service health | ✅ Working |

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Embedding (single doc) | ~500ms | All-MiniLM-L6-v2 |
| Index building (30 chunks) | ~2s | One-time cost |
| Query retrieval | <3ms | On tiny index |
| generate_answer() | <1ms | Mock (no LLM call) |

---

## Limitations (Critical)

1. **FAISS index starts empty.** No documents are pre-loaded. First use must call `/index`.
2. **`generate_answer()` is a mock.** The pipeline retrieves chunks but the answer is a template string, not an LLM-generated response.
3. **Tiny corpus.** 15 documents → ~30 chunks is not a meaningful RAG evaluation.
4. **PDF loader is a stub.** PDF files cannot be parsed.
5. **No document update mechanism.** Re-indexing requires full rebuild.
6. **No filtering or metadata search.** All chunks searched indiscriminately.
