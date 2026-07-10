# Runtime, Climate, and Copilot Integration

The three layers of the BHAI platform integrate through well-defined interfaces, with strict dependency direction: Copilot → Climate → Runtime. Never the reverse.

## Dependency Direction

```
copilot/clients/       → climate/providers/    (wrapped as provider adapters)
climate/plugin.py      → runtime/              (plugin registers into runtime)
runtime/               → (nothing external)    (domain-agnostic core)
```

The Runtime has zero knowledge of Climate or Copilot. The Climate plugin is registered into the Runtime at startup. The Copilot clients are wrapped by Climate provider adapters.

## Startup Sequence

```
1. AgentRuntime.initialize()
   ├── Blackboard created
   ├── EventBus created
   ├── ProviderRegistry created
   ├── CapabilityRouter created
   ├── PluginLoader created
   ├── WorkflowEngine created
   └── PipelineEngine created

2. ClimatePlugin loaded via rt.load_plugin(ClimatePlugin())
   ├── register_capabilities(router)    → 6 contracts registered
   ├── register_providers(registry)     → 6 adapters registered
   ├── register_events(bus)             → publishes domain events
   ├── register_workflows(engine)       → COPILOT_WORKFLOW registered
   └── register_pipelines(runtime)      → climate.interactive pipeline registered

3. Runtime ready to process("user_query", ctx)
   ├── PipelineEngine finds climate.interactive pipeline
   ├── Pipeline executes 11 stages
   │   ├── IntentStage classifies intent
   │   ├── MemoryStage loads conversation context
   │   ├── RetrievalStage queries knowledge providers
   │   ├── PlanningStage builds execution graph
   │   ├── ExecutionStage calls provider adapters
   │   │   └── ForecastProviderAdapter wraps ForecastClient
   │   │   └── RiskProviderAdapter wraps RiskClient
   │   │   └── ... (adapters execute through provider interface)
   │   ├── EvidenceAggregationStage converts to Evidence
   │   ├── GroundingStage verifies claims
   │   ├── ReasoningStage produces conclusions
   │   ├── ResponseStage formats output
   │   └── VerificationStage validates output
   └── RuntimeResult returned
```

## Integration Points

### Plugin Interface

The `Plugin` ABC (`runtime/plugins/base.py`) defines 7 registration methods that the ClimatePlugin implements:

```python
class Plugin(ABC):
    def register_capabilities(self, router): ...
    def register_providers(self, registry): ...
    def register_events(self, bus): ...
    def register_workflows(self, engine): ...
    def register_agents(self, runtime): ...
    def register_configuration(self, runtime): ...
    def register_pipelines(self, runtime): ...
```

### Provider Interface

The `Provider` ABC (`runtime/providers/base.py`) defines the contract that all climate provider adapters implement:

```python
class Provider(ABC):
    provider_id: str
    capability: str
    async def execute(self, request: ProviderRequest) -> ProviderResult: ...
    def health(self) -> ProviderHealth: ...
```

### Pipeline Stage Interface

The `PipelineStage` ABC (`runtime/models/pipeline.py`) defines the lifecycle hooks that pipeline stages implement. Climate stages (Intent, Planning, Execution, Response, Verification) and Runtime stages (Memory, Retrieval, EvidenceAggregation, Grounding, Reasoning) both implement this interface, making them interchangeable in pipeline definitions.

### Event Interface

Both Runtime and Climate define event type constants that flow through the shared EventBus. Runtime events (`runtime/events/definitions.py`) cover memory, retrieval, evidence, grounding, reasoning, and verification lifecycle. Climate events (`climate/events/definitions.py`) cover query processing, domain execution, and response lifecycle.

## Data Flow Summary

```
User → Runtime API → PipelineEngine → [10 Stages] → RuntimeResult
                         ↕
                    Blackboard (shared state store)
                         ↕
                    CapabilityRouter → ProviderRegistry
                         ↕
                    Provider Adapters → Copilot Clients
```

## Testing Integration

Integration tests in `climate/tests/test_integration.py` verify that the ClimatePlugin correctly wires all components together. The plugin test (`climate/tests/test_plugin.py`) validates registration order and contract validation.
