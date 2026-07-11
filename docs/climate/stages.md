# Climate Pipeline Stages

> **Note:** Pipeline stages are defined in `climatedt/pipeline/`. They work with the AI Runtime's PipelineEngine (`runtime/pipeline/`).

## Overview

The climate pipeline extends the Runtime's pipeline system with domain-specific stages. These stages integrate with the Runtime's Blackboard for inter-stage communication and EventBus for observability.

## Stage Descriptions

### 1. IntentStage (`climatedt/pipeline/stages/intent_stage.py`)

Classifies user intent and extracts entities from the raw query using pattern matching — no ML, no external services.

- **Reads**: Blackboard key `query.raw`
- **Writes**: `pipeline.intent` with classified intent context

**Intent types**: forecast, risk, twin_state, scenario, knowledge, report, greeting, unknown

**Entity extraction**: location (from supported locations), days, scenario_type, report_type, top_k

**Compound query detection**: splits queries by "and", "also", "then", ";" and classifies each part independently.

### 2. PlanningStage (`climatedt/pipeline/stages/planning_stage.py`)

Generates an execution graph from the intent and capability metadata. Metadata-driven — no hardcoded tool chains.

- **Reads**: `pipeline.intent`
- **Writes**: `execution_graph` with dependency-resolved capability chain

Resolves the full dependency chain for the primary capability (e.g., report → [forecast, risk, twin_state, knowledge, report]).

### 3. ExecutionStage (`climatedt/pipeline/stages/execution_stage.py`)

Orchestrates capability execution through the CapabilityRouter. Does NOT contain domain logic — it coordinates provider execution.

- **Reads**: `execution_graph`
- **Writes**: `provider_results`

Resolves the execution graph into parallel-executable layers. Each layer executes concurrently using `asyncio.gather()`.

### 4. ResponseStage (`climatedt/pipeline/stages/response_stage.py`)

Formats pipeline results into a user-facing Markdown response. Presentation only — no business logic.

- **Reads**: reasoning output or provider results
- **Writes**: `pipeline.response` as formatted Markdown

Handles confidence-based wording, greeting intents, and unknown intents.

### 5. VerificationStage (`climatedt/pipeline/stages/verification_stage.py`)

Validates the pipeline output — evidence coverage, grounding completeness, citation coverage, numerical consistency, unit formatting, and confidence.

- **Reads**: response, intent, citations, provider results, evidence list
- **Writes**: `pipeline.verified` validation result

**Checks performed**:
1. Response presence and minimum length
2. Citation coverage for knowledge queries
3. Provider error counts
4. Evidence availability
5. Grounding passage
6. Numerical consistency (inverted range detection)
7. Unit formatting (use °C instead of "degree celsius")
8. Markdown formatting presence
9. Low-confidence phrases detection

If validation fails and `regenerate_count < 1`, the stage requests regeneration.

## Data Status

All pipeline stages operate on **synthetic data**. The stages are functional but have never processed real climate data end-to-end.
