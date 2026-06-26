# SYSTEM INSTRUCTION & PROJECT EXECUTION

**Project:** AI-Powered Digital Twin of India's Climate using Indian National Data (ISRO BAH 2026 — Challenge 5)
**Phase Number:** 8
**Phase Name:** Climate Knowledge Base & Retrieval-Augmented Generation (RAG)
**Status:** ✅ Completed
**Priority:** High
**Estimated Duration:** 5–8 Days
**Dependencies:** ✅ Phase 1 | ✅ Phase 2 | ✅ Phase 3 | ✅ Phase 4 | ✅ Phase 5 | ✅ Phase 6 | ✅ Phase 7 Completed
**Version:** 1.0
**Document Owner:** Lead ML/Software Engineer
**Last Updated:** 2026-06-26

## 1. GLOBAL AGENT INSTRUCTIONS

## Startup Procedure

Before beginning work:

1. Verify `AGENT.md` exists.
2. Create it if missing.
3. Read the complete project history.
4. Resume from the latest unfinished task.
5. Never overwrite logs.
6. Append a new session log after every work session.
7. Every log entry must contain:

```text
Phase 8 – Climate Knowledge Base & RAG System
```

---

# PHASE OBJECTIVE

Build a Retrieval-Augmented Generation (RAG) system that allows the Digital Twin to answer questions using trusted climate information instead of relying only on an LLM.

The system should retrieve information from:

* Government climate reports
* Meteorological documentation
* Historical observations
* Model predictions
* Scenario simulations
* Climate risk reports
* Generated project reports

The retrieved context will later be passed to the Climate Copilot.

---

# DESIGN PRINCIPLES

The Knowledge Base should be:

* Accurate
* Traceable
* Modular
* Searchable
* Extensible
* Source-aware

Every answer should be grounded in retrieved evidence.

---

# ARCHITECTURE

```text
Climate Documents
        │
Prediction Reports
        │
Scenario Reports
        │
Risk Reports
        │
Historical Climate Data
        │
        ▼
Document Loader
        │
        ▼
Chunking Engine
        │
        ▼
Embedding Engine
        │
        ▼
Vector Database
        │
        ▼
Retriever
        │
        ▼
Context Builder
        │
        ▼
Climate Copilot
```

---

# DIRECTORY STRUCTURE

```text
knowledge/

├── documents/
│
├── loaders/
│
├── chunkers/
│
├── embeddings/
│
├── vector_store/
│
├── retriever/
│
├── pipelines/
│
├── reports/
│
├── configs/
│
└── api/
```

---

# KNOWLEDGE SOURCES

## Government Documents

Store under:

```text
knowledge/documents/government/
```

Sources include:

* IMD Climate Reports
* IMD Heatwave Guidelines
* IMD Monsoon Reports
* IMD Rainfall Statistics

---

## Satellite Documentation

Store under:

```text
knowledge/documents/isro/
```

Sources:

* INSAT Product Documentation
* MOSDAC Documentation
* Satellite Metadata

---

## Scientific Literature

Store under:

```text
knowledge/documents/research/
```

Examples:

* Climate forecasting
* Time-series prediction
* Digital Twin architecture
* Explainable AI
* Climate adaptation

---

## Generated Project Reports

Automatically index:

* Forecast Reports
* Simulation Reports
* Risk Reports
* Climate Insights
* Dashboard Exports

---

# DOCUMENT INGESTION

Supported formats:

* PDF
* Markdown
* TXT
* CSV
* JSON

Future support:

* HTML
* DOCX

---

# CHUNKING STRATEGY

Chunk Size:

* 500–800 tokens

Chunk Overlap:

* 100–150 tokens

Metadata:

* Source
* Title
* Section
* Page Number
* Date
* Category

---

# EMBEDDING MODEL

Recommended:

Sentence Transformers

Examples:

* all-MiniLM-L6-v2
* BAAI/bge-small-en-v1.5

Embedding dimension should remain configurable.

---

# VECTOR DATABASE

Preferred:

FAISS

Future alternatives:

* ChromaDB
* Qdrant
* Milvus
* PostgreSQL + pgvector

---

# RETRIEVAL STRATEGY

Implement:

* Semantic Search
* Metadata Filtering
* Hybrid Search (future)
* Top-K Retrieval
* Score Threshold Filtering

---

# METADATA SCHEMA

Every indexed chunk should contain:

```text
Document ID

Title

Source

Category

Date

Region

Keywords

Page Number

Chunk Number
```

---

# INDEXING PIPELINE

```text
Load Document
      │
      ▼
Clean Text
      │
      ▼
Chunk Document
      │
      ▼
Generate Embeddings
      │
      ▼
Store in Vector DB
      │
      ▼
Verify Index
```

---

# RETRIEVAL API

Expose:

```python
index_document()

delete_document()

search()

semantic_search()

retrieve_context()

list_sources()

rebuild_index()
```

---

# SEARCH EXAMPLES

Users should be able to ask:

* What causes delayed monsoon?

* Explain rainfall variability.

* Why is this district classified as high drought risk?

* Compare current conditions with historical averages.

* Which variables influenced today's prediction?

---

# CONFIGURATION

Create:

```text
configs/rag.yaml
```

Include:

* Chunk size
* Chunk overlap
* Embedding model
* Retrieval count
* Score threshold
* Vector database path

---

# LOGGING

Create:

```text
logs/rag.log
```

Log:

* Documents indexed
* Retrieval queries
* Search latency
* Embedding generation
* Errors

---

# TESTING REQUIREMENTS

Validate:

* PDF ingestion
* Markdown ingestion
* Embedding generation
* Vector indexing
* Retrieval accuracy
* Metadata filtering
* Context generation

---

# DOWNLOAD SOURCES

## IMD

https://www.imd.gov.in/

Climate Reports

Heatwave Guidelines

Monsoon Reports

---

## MOSDAC

https://www.mosdac.gov.in/

Satellite Products

INSAT Documentation

---

## ISRO Bhuvan

https://bhuvan.nrsc.gov.in/

Geospatial datasets

---

## National Information System for Climate and Environment Studies (NICES)

https://nices-dst.gov.in/

Climate datasets and reports

---

## CODING STANDARDS
* PEP8 compliant Python with type hints.
* Docstrings on all modules, classes, and functions.
* SOLID principles: loaders, chunkers, embeddings, retriever as separate modules.
* Configuration over hardcoding: chunk size, overlap, model name in YAML.
* Extensible design for new document formats and vector databases.
* Production-ready error handling for document parsing failures.

## QUALITY GATES
Before marking phase complete:
* Run formatter and linter.
* Run all RAG pipeline tests.
* Verify PDF and Markdown ingestion works.
* Verify embeddings generate correctly.
* Verify semantic search returns relevant results.
* Verify metadata filtering works as expected.
* Remove dead code.

## DEFINITION OF DONE
Phase 8 is complete ONLY IF:
* [x] Document loaders complete (PDF, MD, TXT, CSV, JSON).
* [x] Chunking engine operational (configurable size/overlap).
* [x] Embedding pipeline generates vectors.
* [x] Vector database (FAISS) configured and populated.
* [x] Retrieval engine supports semantic search and metadata filtering.
* [x] Search APIs implemented and tested.
* [x] `configs/rag.yaml` created.
* [x] `logs/rag.log` enabled.
* [x] All tests pass.
* [x] No TODOs or broken imports.
* [x] Lint passes.
* [x] Documentation updated and AGENT.md appended.

# DELIVERABLES

* Document Loader
* Chunking Engine
* Embedding Pipeline
* Vector Database
* Retriever
* Metadata Manager
* Context Builder
* Search APIs

---

# ACCEPTANCE CRITERIA

* Documents successfully indexed.

* Vector database operational.

* Semantic search functional.

* Metadata filtering operational.

* Context generation complete.

* APIs tested.

* Logging operational.

* AGENT.md updated.

---

# PHASE COMPLETION CHECKLIST

* [x] Document loaders complete

* [x] Chunking engine complete

* [x] Embedding pipeline complete

* [x] Vector database configured

* [x] Retrieval engine complete

* [x] Search APIs implemented

* [x] Logging enabled

* [x] Documentation updated

* [x] AGENT.md appended

---

# NEXT PHASE

## Phase 9 — Climate Copilot

Objectives:

* Integrate the RAG pipeline with a lightweight LLM.
* Build a conversational Climate Copilot.
* Generate grounded explanations, reports, and recommendations.
* Provide natural language access to the Digital Twin, forecasts, simulations, and risk assessments.
