# CopilotWorkflow

The CopilotWorkflow (`climate/workflows/copilot.py`) is a legacy workflow definition that provides backward compatibility with the Phase 1 workflow-based execution model. It is registered by the ClimatePlugin as a fallback when the pipeline engine doesn't find a matching pipeline.

## Workflow Definition

```python
from runtime.models.workflow import WorkflowDefinition, WorkflowStep

COPILOT_WORKFLOW = WorkflowDefinition(
    id="copilot.default",
    name="Climate Copilot Query",
    version="1.0.0",
    description="Process a user query through intent classification, "
                "domain execution, and response generation",
    triggers=["user_query"],
    steps=[
        WorkflowStep(
            id="classify_intent",
            capability="knowledge",
            params={"query": "{query.raw}"},
        ),
        WorkflowStep(
            id="execute_domain",
            capability="forecast",
            params={"query": "{query.raw}"},
            depends_on=["classify_intent"],
        ),
        WorkflowStep(
            id="generate_response",
            capability="scenario",
            params={
                "intent": "{step.classify_intent}",
                "results": "{step.execute_domain}",
            },
            depends_on=["execute_domain"],
        ),
    ],
    timeout_ms=60000,
)
```

## Execution Flow

The WorkflowEngine executes steps as a DAG. Steps declare dependencies via `depends_on`, and the engine resolves them into execution layers:

1. **classify_intent**: calls the "knowledge" provider to classify the intent
2. **execute_domain**: calls the "forecast" provider with the classified intent (depends on step 1)
3. **generate_response**: calls the "scenario" provider with intent and results (depends on step 2)

Parameter templates like `{query.raw}` and `{step.classify_intent}` are resolved at execution time from the runtime context.

## Capability Resolution

The workflow engine uses the CapabilityRouter to find a provider for each step's capability. The router selects the best provider from the ProviderRegistry based on availability and deterministic preference.

## Pipeline vs Workflow

The Runtime's `process()` method prefers pipeline execution:

```python
# In AgentRuntime.process():
pipeline = self.pipeline_engine.find(trigger)
if pipeline:
    # Execute pipeline (preferred)
else:
    # Fallback to workflow (legacy)
    result = await self.execute_workflow(trigger, context)
```

When the ClimatePlugin is loaded, the `climate.interactive` pipeline (11 stages) takes precedence over the COPILOT_WORKFLOW for "user_query" triggers. The workflow remains registered for backward compatibility and can be used directly for custom triggers.

## Workflow Engine

The WorkflowEngine (`runtime/workflow/engine.py`) manages workflow registration and execution:

```python
engine = WorkflowEngine(
    provider_registry=registry,
    capability_router=router,
    blackboard=blackboard,
    event_bus=event_bus,
)
engine.register(COPILOT_WORKFLOW)
result_data = await engine.execute(workflow, context)
```

It resolves step dependencies, executes steps through the capability system, handles parameter templating, and collects results.
