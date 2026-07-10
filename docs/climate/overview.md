# Climate Plugin

The Climate plugin (`climate/plugin.py`) is a Runtime plugin that wires the climate domain into the platform. It is the only source of domain-specific logic — the Runtime has no knowledge of climate concepts.

## Registration Pattern

The `ClimatePlugin` implements the `Plugin` interface from `runtime/plugins/base.py` and registers its domain artifacts through 6 plugin hooks:

```python
class ClimatePlugin(Plugin):
    name = "climate"
    version = "0.1.0"
    description = "Climate Digital Twin domain capabilities"

    def register_capabilities(self, router: CapabilityRouter) -> None:
        # Registers 6 capability contracts
        for cap in ALL_CAPABILITIES:
            router.register(cap)

    def register_providers(self, registry: ProviderRegistry) -> None:
        # Registers 6 provider adapters (migration wrappers)
        for cap_name, adapter_cls, entry in _PROVIDER_CONFIGS:
            registry.register(cap_name, adapter_cls())

    def register_workflows(self, engine: WorkflowEngine) -> None:
        # Registers COPILOT_WORKFLOW (backward compat)
        engine.register(COPILOT_WORKFLOW)

    def register_pipelines(self, runtime) -> None:
        # Registers climate.interactive pipeline with 11 stages
        pipeline = CognitivePipeline(
            id="climate.interactive",
            triggers=["user_query"],
            stages=[...],
        )
        runtime.register_pipeline(pipeline)
```

## Capabilities

6 capabilities registered by the Climate plugin:

| Capability | Description | Dependencies | Default Timeout |
|------------|-------------|-------------|-----------------|
| forecast | Climate forecast (temp, rainfall, 7 days) | None | 10,000ms |
| risk | Risk scores (heat, flood, drought, composite) | forecast | 10,000ms |
| twin_state | Digital twin current state | None | 10,000ms |
| scenario | What-if scenario simulation | forecast, twin_state | 15,000ms |
| knowledge | Semantic knowledge base search | None | 10,000ms |
| report | Structured climate report | forecast, risk, twin_state, knowledge | 20,000ms |

Each capability is defined as a `CapabilityType` in `climate/capabilities/contracts.py` with input/output JSON schemas, timeout/retry/cache policies, and dependency metadata.

## Architecture

See `reports/diagrams/climate_architecture.md` for the complete Mermaid diagram.

```
ClimatePlugin
  ├── register_capabilities → CapabilityRouter (6 contracts)
  ├── register_providers → ProviderRegistry (6 adapters)
  ├── register_workflows → WorkflowEngine (COPILOT_WORKFLOW)
  └── register_pipelines → PipelineEngine (climate.interactive)
       ├── IntentStage (climate)
       ├── MemoryStage (runtime)
       ├── RetrievalStage (runtime)
       ├── PlanningStage (climate)
       ├── ExecutionStage (climate)
       ├── EvidenceAggregationStage (runtime)
       ├── GroundingStage (runtime)
       ├── ReasoningStage (runtime)
       ├── ResponseStage (climate)
       └── VerificationStage (climate)
```

## Migration Wrapper Status

All 6 provider adapters are migration wrappers targeting Phase 4 removal:

| Adapter | Wraps Legacy Client | Phase |
|---------|-------------------|-------|
| ForecastProviderAdapter | copilot.clients.ForecastClient | Phase 4 |
| RiskProviderAdapter | copilot.clients.RiskClient | Phase 4 |
| TwinStateProviderAdapter | copilot.clients.TwinClient | Phase 4 |
| ScenarioProviderAdapter | copilot.clients.ScenarioClient | Phase 4 |
| KnowledgeProviderAdapter | copilot.clients.RAGClient | Phase 4 |
| ReportProviderAdapter | copilot.clients.ReportClient | Phase 4 |

The `MigrationRegistry` in `climate/migration_registry.py` tracks all migration entries with source, target, adapter, status, and target phase.
