# Climate Domain Plugin

> **Note:** Climate domain logic is in the `climatedt/` package (NOT `climate/`). This document describes how the climate domain integrates with the AI Runtime.

## Overview

The climate domain logic (`climatedt/`) contains all climate-specific code organized into sub-packages:

```
climatedt/
├── ml/          Model training and prediction
├── pipeline/    Pipeline stages (intent, planning, execution, response, verification)
├── rag/         Retrieval-Augmented Generation
├── risk/        Risk assessment logic
├── scenario/    Scenario simulation
├── storage/     Data storage layer
├── twin/        Digital twin state management
└── feedback/    Feedback handling
```

## Key Components

### ML (`climatedt/ml/`)
Model training and inference pipelines that can run on synthetic data. These are wrappers around the model definitions in `models/`.

### Pipeline (`climatedt/pipeline/`)
Climate-specific pipeline stages that extend the Runtime's PipelineEngine:
- **Intent**: Classifies user intent from query text
- **Planning**: Builds execution graph from intent
- **Execution**: Orchestrates provider calls
- **Response**: Formats results as Markdown
- **Verification**: Validates pipeline output

### RAG (`climatedt/rag/`)
RAG knowledge base integration that interfaces with the `knowledge/` package (FAISS + sentence-transformers).

### Risk (`climatedt/risk/`)
Climate risk assessment logic (heat, flood, drought, composite risk) wrapping the risk engine in `risk/`.

### Scenario (`climatedt/scenario/`)
Scenario simulation logic wrapping the simulator in `simulator/`.

### Twin (`climatedt/twin/`)
Digital twin state management coordinating with the `twin-state-mgr` service.

## Integration with Runtime

The climate domain integrates with the AI Runtime (`runtime/`) through:
1. **Pipeline stages** that implement the Runtime's PipelineStage interface
2. **Provider adapters** that implement the Runtime's Provider interface
3. **Service clients** that call backend microservices via HTTP

## Data Status

**All climate data in this package is synthetic.** No real weather observations, forecast data, or climate records have been ingested. The NASA POWER API integration exists in code but defaults to synthetic data generation.
