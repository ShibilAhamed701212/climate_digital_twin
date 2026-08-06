# Knowledge Base & RAG Engine

## Overview

The **Knowledge Base & RAG Service** (`knowledge/`) equips the Climate Digital Twin with domain knowledge retrieval capabilities. It ingests weather agency reports, government adaptation plans, satellite observation manuals, and climate research papers, enabling semantic search and grounding AI Copilot responses in verified domain literature.

---

## Architecture & Components

```
Documents (Markdown, CSV, JSON) ──► Document Loaders ──► Chunkers (Recursive/Token)
                                                               │
                                                               ▼
FAISS Vector Store ◄── Embeddings (`sentence-transformers`) ◄───┘
       │
       ▼
Hybrid Search (Semantic FAISS + Lexical BM25) ──► Context Builder ──► RAG API / Copilot
```

---

## Key Modules

### 1. Document Loaders & Chunkers (`knowledge/loaders/`, `knowledge/chunkers/`)
- Supports structured and unstructured document formats (Markdown, CSV, JSON, TXT).
- Implements semantic chunking with configurable overlap to preserve contextual boundaries.

### 2. Sentence Transformers & Vector Store (`knowledge/embeddings/`, `knowledge/vector_store/`)
- Uses pre-trained sentence transformers (`all-MiniLM-L6-v2`) to produce dense vector representations.
- Utilizes **FAISS** (Facebook AI Similarity Search) for high-performance vector indexing.

### 3. Hybrid Search Retriever (`knowledge/retriever/hybrid_search.py`)
Combines two search paradigms using Reciprocal Rank Fusion (RRF):
- **Dense Retrieval**: Captures semantic intent using vector similarity.
- **Sparse Retrieval**: BM25 lexical matching for domain terms, location names, and precise thresholds.

### 4. Context Builder (`knowledge/retriever/context_builder.py`)
Formats retrieved document chunks into clean markdown context prompts for LLM response generation.

---

## Document Collections (`knowledge/documents/`)

| Collection | Source / Topic | Description |
|---|---|---|
| `imd/` | Weather Agency Reports | Regional climate statistics, monsoon tracking, seasonal bulletins |
| `isro/` | Remote Sensing Manuals | Satellite climate observation guidelines, land surface products |
| `government/` | Policy & Action Plans | Climate adaptation policies, disaster management guidelines |
| `risk/` | Vulnerability Studies | Flood maps, drought mitigation frameworks, heatwave guidelines |
| `research/` | Academic Literature | Climate change projections and regional impact studies |

---

## Indexing Documents

To index new or updated documents into the vector store:

```bash
python scripts/index_knowledge_base.py
```
