# Runtime Architecture

## Overview
Domain-agnostic platform for executing agent workflows. Zero climate/weather/domain logic.

## Components
- Blackboard: versioned key-value store with watchers
- EventBus: async pub/sub with trace_id propagation
- Provider: interface for executing capabilities
- CapabilityRouter: register/resolve/validate capability contracts
- Plugin: interface for domain packages to register with Runtime
- WorkflowEngine: DAG execution with parallel steps
- Lifecycle: formal INIT -> REGISTER -> VALIDATE -> START -> RUN -> SHUTDOWN

## Lifecycle
Initialize: UNINITIALIZED -> INITIALIZING -> RUNNING
Shutdown: RUNNING -> SHUTTING_DOWN -> STOPPED
Recover: STOPPED -> RECOVERING -> RUNNING
