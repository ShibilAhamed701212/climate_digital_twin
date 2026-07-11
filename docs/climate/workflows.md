# Climate Workflows

> **Note:** Workflow definitions are in `copilot/workflows/`. They work with the AI Runtime's WorkflowEngine (`runtime/workflow/`).

## Overview

The CopilotWorkflow is a legacy workflow definition that provides backward compatibility with workflow-based execution. It is registered as a fallback when the pipeline engine doesn't find a matching pipeline.

## Workflow Definition

Workflows define multi-step processing chains:

```python
from runtime.models.workflow import WorkflowDefinition, WorkflowStep

COPILOT_WORKFLOW = WorkflowDefinition(
    id="copilot.default",
    name="Climate Copilot Query",
    triggers=["user_query"],
    steps=[
        WorkflowStep(id="classify_intent", capability="knowledge", ...),
        WorkflowStep(id="execute_domain", capability="forecast", ...),
        WorkflowStep(id="generate_response", capability="scenario", ...),
    ],
)
```

## Execution Flow

The WorkflowEngine executes steps as a DAG. Steps declare dependencies via `depends_on`, and the engine resolves them into execution layers with parallel execution where possible.

## Pipeline vs Workflow

The Runtime's `process()` method prefers pipeline execution. When a pipeline is registered for a trigger, pipelines take precedence. Workflows serve as a fallback mechanism.

## Data Status

All workflow execution uses **synthetic data**. No real service integration.
