# Climate Pipeline Stages

In addition to the 5 runtime-native stages, the Climate plugin contributes 5 domain-specific stages that handle intent classification, execution orchestration, response composition, and output verification.

## 1. IntentStage (`climate/pipeline/stages/intent_stage.py`)

Classifies user intent and extracts entities from the raw query using pure pattern matching — no ML, no external services.

- **Reads**: Blackboard key `query.raw`
- **Writes**: `stage_outputs["intent"]` = `IntentContext`, Blackboard `pipeline.intent`

**Intent types**: forecast, risk, twin_state, scenario, knowledge, report, greeting, unknown

**Entity extraction**: location (from 36 supported Indian locations), days, scenario_type (temperature/rainfall/monsoon/extreme_event), report_type (summary/detailed/risk/forecast), top_k

**Compound query detection**: splits queries by "and", "also", "then", ";" and classifies each part independently. Selects the highest-confidence intent as primary and records ambiguity flags.

```python
# Query: "forecast for Bangalore and risk for Chennai"
# → compound intent, primary=forecast, ambiguity=[forecast, risk]
```

Publishes events: `QUERY_NORMALIZED`, `INTENT_RESOLVED`.

## 2. PlanningStage (`climate/pipeline/stages/planning_stage.py`)

Generates an execution graph from the intent and capability metadata. Metadata-driven — no hardcoded tool chains.

- **Reads**: `stage_outputs["intent"]` = IntentContext
- **Reads**: `CAPABILITY_MAP` for capability metadata (dependencies, cost, latency, parallelizable)
- **Writes**: `stage_outputs["execution_graph"]` = ExecutionGraph, `stage_outputs["capability_selection"]` = CapabilitySelection

Resolves the full dependency chain for the primary capability. For example, if the intent is "report", the dependency chain becomes: [forecast, risk, twin_state, knowledge, report].

Each step includes:
- capability name and parameters
- dependency references
- timeout, retry count, failure policy
- estimated cost and latency

Publishes events: `EXECUTION_GRAPH_CREATED`, `CAPABILITY_RESOLVED`.

## 3. ExecutionStage (`climate/pipeline/stages/execution_stage.py`)

Orchestrates capability execution through the CapabilityRouter. This stage does NOT contain domain logic — it coordinates provider execution.

- **Reads**: `stage_outputs["execution_graph"]` = ExecutionGraph
- **Writes**: `stage_outputs["provider_results"]` = ProviderResults, Blackboard `pipeline.provider_results`

Resolves the execution graph into parallel-executable layers based on dependency order. Each layer executes concurrently using `asyncio.gather()`. Each step is executed through `run_provider_safely()` which handles:
- Async/sync provider detection (sync runs in thread pool)
- Timeout enforcement
- Exception wrapping
- Retry with exponential backoff (per-step `max_retries`)

Collects all results into a `ProviderResults` object with success/failure counts and total latency.

## 4. ResponseStage (`climate/pipeline/stages/response_stage.py`)

Formats pipeline results into a user-facing Markdown response. Presentation only — no business logic, no fact invention.

- **Reads**: `stage_outputs["reasoning"]` (preferred), `stage_outputs["provider_results"]` (fallback), `stage_outputs["intent"]`
- **Writes**: `stage_outputs["response"]` = str, Blackboard `pipeline.response`, `pipeline.response_draft`

Phase 3 path (preferred): formats `ReasoningOutput` into a structured Markdown response with Key Findings, Assumptions, and Uncertainties sections with confidence indicators.

Legacy fallback path: formats `ProviderResults` with capability-specific formatting for each domain (forecast tables, risk scores, twin state, scenario results, knowledge citations, report text).

Confidence wording is selected from a lookup table based on intent confidence score (0.0 → "I'm not sure" through 0.95 → "Here are the detailed results for").

Handles greeting intents with randomized welcome messages and unknown intents with a clear error message.

Publishes event: `RESPONSE_DRAFTED`.

## 5. VerificationStage (`climate/pipeline/stages/verification_stage.py`)

Validates the pipeline output — evidence coverage, grounding completeness, citation coverage, numerical consistency, unit formatting, and confidence.

- **Reads**: `stage_outputs["response"]`, `stage_outputs["intent"]`, `stage_outputs["citations"]`, `stage_outputs["provider_results"]`, Blackboard `evidence.list`, Blackboard `grounding.report`
- **Writes**: `stage_outputs["validation"]` = ValidationResult, Blackboard `pipeline.verified`

Checks performed:
1. Response presence and minimum length (20 chars for substantive queries)
2. Citation coverage for knowledge queries
3. Provider error counts
4. Evidence availability (Phase 3)
5. Grounding passage (Phase 3)
6. Numerical consistency (inverted range detection)
7. Unit formatting (use °C instead of "degree celsius")
8. Markdown formatting presence (headers, bold, lists)
9. Low-confidence phrases ("I'm sorry", "I cannot", "unable to")

If validation fails and `regenerate_count < 1`, the stage sets `regeneration_requested = True`, triggering the PipelineEngine to re-execute the response stage.

Publishes event: `RESPONSE_VALIDATED`.
