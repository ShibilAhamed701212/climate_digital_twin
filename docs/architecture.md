# System Architecture

The BHAI Climate Digital Twin is architected as a three-layer platform: **Runtime** (domain-agnostic orchestration engine), **Climate** (domain plugin), and **Copilot** (legacy client adapters). The architecture enforces strict layer isolation: Runtime contains zero domain-specific concepts, validated by automated architecture tests in `runtime/test_architecture.py`.

## Layers

### Runtime Core

The Runtime is the execution platform. It owns:

- **AgentRuntime** (`runtime/runtime.py`): orchestrator that initializes all subsystems, loads plugins, dispatches to pipeline or workflow, and manages lifecycle
- **PipelineEngine** (`runtime/pipeline/engine.py`): loads pipeline definitions, resolves DAG execution order, executes stages with lifecycle hooks (before_execute, execute, after_execute, on_error, on_timeout)
- **Blackboard** (`runtime/blackboard.py`): thread-safe, versioned, key-value store with TTL, bounded history (100 versions per key), watchers, and glob-query
- **EventBus** (`runtime/event_bus.py`): pub/sub event system with bounded deque (10,000 events), trace IDs, and thread-safe dispatch
- **Infrastructure**: caching (`runtime/cache/`), metrics & logging (`runtime/observability.py`), circuit breaker & retry (`runtime/reliability.py`), distributed tracing (`runtime/tracing.py`)
- **Data Models**: Evidence, Memory, RetrievalResult, GroundingResult, ReasoningOutput, RuntimeContext, ExecutionContext, ProviderRequest/Result
- **Architecture tests**: enforce that `runtime/` contains no domain terms (climate, weather, rainfall, etc.) and no imports from `climate/` or `copilot/`

See `reports/diagrams/runtime_architecture.md` for the Mermaid diagram.

### Climate Plugin

The Climate domain is a Runtime plugin (`climate/plugin.py`). It registers:

- 6 capabilities: forecast, risk, twin_state, scenario, knowledge, report
- 6 provider adapters wrapping legacy Copilot clients
- 5 climate-specific pipeline stages: Intent, Planning, Execution, Response, Verification
- 1 workflow definition: COPILOT_WORKFLOW (backward compatibility)

All adapters are marked as migration wrappers targeting Phase 4 removal. The pipeline (`climate.interactive`) registers 11 stages total — 5 climate + 5 runtime + 1 shared evidence aggregation.

See `reports/diagrams/climate_architecture.md` for the Mermaid diagram.

### Copilot Clients

The `copilot/clients/` package contains five lightweight client classes (ForecastClient, RiskClient, TwinClient, RAGClient, ReportClient) that return mock data. These are the legacy interfaces being migrated to Runtime provider adapters. No new code should depend on them directly.

## Pipeline Architecture

The cognitive pipeline processes user queries through up to 10 stages, communicating through the Blackboard. See `reports/diagrams/pipeline_flow.md` for the Mermaid diagram.

| # | Stage | Source | Blackboard I/O |
|---|-------|--------|---------------|
| 1 | Intent | climate | reads: query.raw → writes: pipeline.intent |
| 2 | Memory | runtime | reads: query.context → writes: memory.* |
| 3 | Retrieval | runtime | reads: pipeline.intent → writes: retrieval.* |
| 4 | Planning | climate | reads: pipeline.context → writes: execution.graph |
| 5 | Execution | climate | reads: execution.graph → writes: provider.results |
| 6 | Evidence Aggregation | runtime | reads: provider.results, retrieval.* → writes: evidence.* |
| 7 | Grounding | runtime | reads: evidence.* → writes: grounding.* |
| 8 | Reasoning | runtime | reads: grounding.*, evidence.* → writes: reasoning.* |
| 9 | Response | climate | reads: reasoning.*, provider.results → writes: pipeline.response |
| 10 | Verification | climate | reads: pipeline.* → writes: pipeline.verified |

## Data Flow

End-to-end flow: see `reports/diagrams/data_flow.md` for the full sequence diagram.

1. User submits query → Runtime API
2. Runtime dispatches to PipelineEngine with "user_query" trigger
3. Pipeline executes stages sequentially, each reading/writing to Blackboard
4. Events published to EventBus at each stage boundary for observability
5. Final response assembled by ResponseStage
6. VerificationStage validates output (evidence coverage, citations, formatting, numerical consistency)
7. If verification fails, one regeneration cycle is allowed

## Key Design Decisions

- **Evidence is immutable**: once created, Evidence objects are not mutated; `with_confidence()` returns a new instance
- **Runtime is domain-agnostic**: verified by AST-level architecture tests
- **Stages communicate through Blackboard only**: no direct stage-to-stage coupling
- **EventBus uses past tense**: events describe completed facts, never commands
- **Memory is structured facts**: never raw prompts or paragraphs; 6 store types with TTL
- **Caching is layered**: 4 caches with different TTL strategies — provider (60s), retrieval (300s), reasoning (600s), resolution (24h)
