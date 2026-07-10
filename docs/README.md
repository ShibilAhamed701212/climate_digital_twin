# BHAI Climate Digital Twin Platform

**Version 0.1.0** — 461 tests passing, 152 Python files, 11,293 LOC, 92.9% type annotation coverage.

An evidence-driven AI Runtime for climate risk analysis. The system processes natural language queries about climate conditions through a cognitive pipeline: intent classification, memory retrieval, knowledge retrieval, planning, provider execution, evidence aggregation, grounding, reasoning, response composition, and verification.

## Architecture at a Glance

```
User Query → Runtime API → Pipeline Engine (10 stages) → Response
                              ↕
                          Blackboard (shared state)
                              ↕
                    ClimatePlugin → 6 Provider Adapters
                    (forecast, risk, twin_state, scenario, knowledge, report)
```

Three layers: **Runtime** (domain-agnostic orchestration), **Climate** (domain plugin), **Copilot** (client adapters). See `docs/architecture.md` for the full picture, and `reports/diagrams/architecture_overview.md` for the Mermaid diagram.

## Quick Start

```python
from runtime.runtime import AgentRuntime
from runtime.models.runtime import RuntimeContext
from climate.plugin import ClimatePlugin

rt = AgentRuntime()
await rt.initialize()

rt.load_plugin(ClimatePlugin())

ctx = RuntimeContext(trace_id="my-query")
result = await rt.process("user_query", ctx)

print(result.response)
await rt.shutdown()
```

## Directory Structure

```
├── runtime/           Core execution infrastructure (domain-agnostic)
│   ├── pipeline/      Pipeline engine + 5 native stages
│   ├── models/        Data models (Evidence, Memory, Retrieval, etc.)
│   ├── cache/         TTL-based caching (4 domain caches)
│   ├── providers/     Provider interface + registry + executor
│   ├── plugins/       Plugin interface + loader
│   ├── agents/        Agent interface
│   ├── workflow/      Workflow engine + definitions
│   ├── capabilities/  Capability contracts + router
│   ├── benchmarks/    67 benchmark tests (8 suites)
│   └── tests/         Unit tests + architecture tests
├── climate/           Climate domain plugin
│   ├── providers/     6 provider adapters (migration wrappers)
│   ├── pipeline/      5 climate pipeline stages
│   ├── workflows/     Copilot workflow definition
│   ├── capabilities/  6 capability contracts
│   └── tests/         Unit + integration tests
├── copilot/           Client adapters (legacy, being migrated)
│   └── clients/       Forecast, Risk, Twin, RAG, Report clients
├── docs/              Documentation (this directory)
└── reports/           Code quality, security audit, diagrams, benchmarks
```

## Key Features

- **Evidence-centered processing**: every provider output becomes immutable Evidence; claims are grounded against evidence before reaching the user
- **Pluggable domain architecture**: Runtime has zero domain knowledge; climate-specific logic is isolated in the ClimatePlugin
- **10-stage cognitive pipeline**: intent → memory → retrieval → planning → execution → evidence aggregation → grounding → reasoning → response → verification
- **Production reliability**: circuit breaker, retry with exponential backoff, TTL caching, bounded memory, structured metrics
- **Docker deployment**: `docker-compose.benchmark.yml` for benchmark execution
