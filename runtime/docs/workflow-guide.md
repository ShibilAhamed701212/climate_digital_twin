# Workflow Guide

Define workflow DAG:
- WorkflowStep(id, capability, params, depends_on)
- WorkflowDefinition(id, name, version, triggers, steps)

Steps with depends_on run after dependencies.
Independent steps run in parallel.
Failure modes: abort (default), skip.
