# AI Runtime

Domain-agnostic agent orchestration platform.

## Architecture

Four layers: Applications -> Domain Packages -> AI Runtime -> Infrastructure.
The Runtime contains zero domain-specific logic.

## Core Containers

- `runtime.blackboard` - Shared versioned state store
- `runtime.event_bus` - Async pub/sub event system
- `runtime.providers` - Provider interface and registry
- `runtime.capabilities` - Capability contracts and router
- `runtime.agents` - Base agent interface
- `runtime.plugins` - Plugin interface and loader
- `runtime.workflow` - Workflow DAG execution engine
- `runtime.lifecycle` - Formal lifecycle management
- `runtime.tracing` - Execution tracing

## Quick Start

```python
from runtime.runtime import AgentRuntime
from runtime.models.runtime import RuntimeContext

rt = AgentRuntime()
await rt.initialize()

ctx = RuntimeContext(trace_id="my-request")
result = await rt.process("trigger", ctx)

await rt.shutdown()
```

Version: 0.1.0
