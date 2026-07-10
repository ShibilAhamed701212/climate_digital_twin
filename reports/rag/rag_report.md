# RAG Knowledge Base Report

## Overview

The RAG (Retrieval-Augmented Generation) Knowledge Base provides semantic search over climate documents for the Climate Digital Twin platform. It ingests documents from 5 source categories, chunks them at configurable sizes, embeds them using Sentence Transformers, and enables vector similarity search via FAISS.

## Vector Store

| Property | Value |
|----------|-------|
| Index Type | FAISS `IndexFlatIP` (Inner Product / cosine similarity) |
| Index File | `knowledge/vector_store/index.faiss` |
| Metadata File | `knowledge/vector_store/metadata.pkl` |
| Index Size (on disk) | 46,125 bytes (45 KB) |
| Metadata Size (on disk) | 110,927 bytes (108 KB) |
| Total Indexed Chunks | 30 |
| Total Document Sources | 15 |
| Embedding Dimension | 384 |
| Distance Metric | Cosine similarity (normalized L2 + Inner Product) |

## Embedding Model

| Property | Value |
|----------|-------|
| Model Name | `all-MiniLM-L6-v2` |
| Provider | Sentence Transformers (`sentence-transformers`) |
| Output Dimension | 384 |
| Fallback | Deterministic hash-based dummy embeddings (MD5 seed, 384-dim) when Sentence Transformers unavailable |

The `EmbeddingModel` class (`knowledge/embeddings/embedding_model.py`) wraps the Sentence Transformers library. On initialization it loads `all-MiniLM-L6-v2`. If the import fails, it falls back to a deterministic pseudo-random embedding based on the text's MD5 hash using a linear congruential generator (`_SimpleRNG`).

### Encoding Methods

- `encode(texts)` — accepts `str` or `list[str]`, returns `list[list[float]]`
- `encode_single(text)` — convenience for single string, returns `list[float]`

## Chunking Strategy

| Parameter | Value |
|-----------|-------|
| chunk_size | 700 tokens (word count) |
| chunk_overlap | 120 tokens |

The `TextChunker` class (`knowledge/chunkers/text_chunker.py`) implements recursive character splitting on natural boundaries:

1. Split on double newlines (paragraph boundaries)
2. If any segment exceeds `chunk_size`, split on single newlines
3. If still too long, split on sentence boundaries (`[.!?]\s+`)
4. If still too long, split on word boundaries

Chunks under the size limit are merged back together. Overlap is applied by appending the last N words of the previous chunk to the current chunk.

Each chunk inherits metadata from its parent Document and gets a unique `chunk_id` via MD5 hash of `"{document_id}-{chunk_number}"`.

## Retrieval Configuration

| Parameter | Value |
|-----------|-------|
| default top_k | 5 |
| score_threshold | 0.5 |
| enable_metadata_filtering | true |

The `SemanticSearch` class (`knowledge/retriever/semantic_search.py`) performs:
1. Query embedding via `EmbeddingModel`
2. Vector search via `FAISSStore.search()` — returns results sorted by cosine similarity
3. Score threshold filter — drops results below 0.5
4. Optional metadata filtering — support for filtering on any `SearchResult` field (category, region, source, etc.)

### RetrievalContext

The `retrieve_context()` method returns a `RetrievalContext` containing:
- `query` — original query string
- `results` — list of `SearchResult` objects
- `context_text` — concatenated formatted results for LLM consumption
- `total_results` — count after filtering
- `filtered_by_metadata` — whether metadata filtering was applied
- `latency_ms` — end-to-end latency in milliseconds

### Context Builder

The `ContextBuilder` class (`knowledge/retriever/context_builder.py`) provides three output formats:
- `build_llm_context()` — Markdown-formatted context string with token limit (max_tokens by word count)
- `build_sectioned_context()` — dictionary grouping results by category
- `format_for_dashboard()` — dashboard-ready dict with sections, query, and latency

## Document Loaders

6 loaders are registered in the factory (`knowledge/loaders/factory.py`):

| Loader | Format | Extension | Class |
|--------|--------|-----------|-------|
| MarkdownLoader | MARKDOWN | `.md` | `knowledge/loaders/md_loader.py` |
| TextLoader | TEXT | `.txt` | `knowledge/loaders/txt_loader.py` |
| CSVLoader | CSV | `.csv` | `knowledge/loaders/csv_loader.py` |
| JSONLoader | JSON | `.json` | `knowledge/loaders/json_loader.py` |
| — | PDF | `.pdf` | Declared in `DocumentFormat` but no loader registered |
| — | — | fallback | Raises `LoaderError` for unsupported formats |

### Loader Details

- **MarkdownLoader**: Extracts title from `# ` heading, auto-generates document_id via MD5 hash of path
- **TextLoader**: Raw text reading with UTF-8 encoding
- **CSVLoader**: Converts tabular data to formatted text (header, columns, row-by-row values)
- **JSONLoader**: Flattens JSON structures via `json.dumps(indent=2)`

All loaders inherit from `BaseLoader` (`knowledge/loaders/base.py`), which provides `_read_raw()` with UTF-8 encoding and raises `LoaderError` on failures.

## Source Categories

5 source categories are indexed from `knowledge/documents/`:

| Category | Directory | Documents |
|----------|-----------|-----------|
| government | `knowledge/documents/government/` | `karnataka_climate_profile.md` |
| imd | `knowledge/documents/imd/` | `imd_weather_data.md` |
| isro | `knowledge/documents/isro/` | `insat_satellite_products.md` |
| research | `knowledge/documents/research/` | `climate_forecasting_methods.md` |
| risk | `knowledge/documents/risk/` | `climate_risk_assessment.md` |

## Indexing Pipeline

The `IndexingPipeline` class (`knowledge/pipelines/indexing_pipeline.py`) orchestrates:

1. **Document Loading** — `guess_format()` determines format from extension, factory returns the matching loader
2. **Chunking** — `TextChunker.chunk_document()` splits into overlapping chunks
3. **Embedding** — `EmbeddingModel.encode()` generates 384-dim vectors
4. **Storage** — `FAISSStore.add()` appends vectors to the FAISS index and persists metadata

The pipeline supports single document indexing (`index_document()`), directory indexing (`index_directory()` with optional recursive traversal), and batch indexing with per-file success/failure tracking via `IndexingResult`.

## API Endpoints

### RAG Knowledge API (`knowledge/api/main.py`)

FastAPI application mounted at the RAG service:

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/health` | GET | Health check | — | `{"status": "healthy", "service": "rag-service", "version": "1.0.0"}` |
| `/search` | POST | Semantic search | `{"query": str, "top_k": int (default 3)}` | `SearchResponse` with results array |

### SearchResponse Model

Each result in the response contains:
- `chunk_id`, `document_id` — unique identifiers
- `title`, `source`, `category` — document metadata
- `content` — chunk text
- `score` — cosine similarity score
- `chunk_number`, `page_number` — position within document
- `date`, `region`, `keywords` — optional metadata

### KnowledgeAPI (`knowledge/api/search_api.py`)

High-level wrapper providing:
- `index_document()`, `index_directory()` — document ingestion
- `search()`, `semantic_search()` — query the knowledge base
- `retrieve_context()` — search with metadata filtering and context assembly
- `delete_document()` — remove a document and its chunks
- `rebuild_index()` — clear and reset the vector store
- `list_sources()`, `get_index_stats()` — knowledge base introspection

## Data Models

All models are defined in `knowledge/models.py` as frozen dataclasses:

- **Document** — source document with full content, metadata, and format enum
- **Chunk** — a single chunk with inherited metadata and position
- **SearchResult** — chunk with similarity score for search responses
- **RetrievalContext** — complete retrieval output with assembled context text
- **IndexingResult** — per-document indexing status (success/failure + chunk count)
- **SourceInfo** — category summary with count and last indexed timestamp
- **DocumentFormat** — enum: PDF, MARKDOWN, TEXT, CSV, JSON

## Configuration

Loaded from `knowledge/configs/rag.yaml` with hardcoded defaults in `knowledge/config_loader.py` (55 lines). If the config file is missing, the system uses defaults silently with a warning log.

## Report Generation

The `IndexReport` class (`knowledge/reports/index_report.py`) generates Markdown and JSON summaries of the indexed knowledge base, listing each source with its chunk count and category.

## Limitations

1. **No PDF loader** — PDF format is declared in the `DocumentFormat` enum but no PDF loader is implemented in the factory
2. **Dummy embedding fallback** — without `sentence-transformers`, retrieval quality degrades to hash-based deterministic noise
3. **Persistence at index level only** — the FAISS index cannot be incrementally updated for deletions; `delete_document()` triggers a full rebuild
4. **No authentication** — API endpoints are open; no auth middleware is present
5. **Single-node FAISS** — no distributed search; all vectors in memory on a single node
