from __future__ import annotations

from enum import StrEnum


class RuntimeLifecycle(StrEnum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    REGISTERING_PLUGINS = "registering_plugins"
    PLUGINS_REGISTERED = "plugins_registered"
    VALIDATING_CONTRACTS = "validating_contracts"
    CONTRACTS_VALIDATED = "contracts_validated"
    STARTING_PROVIDERS = "starting_providers"
    PROVIDERS_STARTED = "providers_started"
    STARTING_AGENTS = "starting_agents"
    AGENTS_STARTED = "agents_started"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    RECOVERING = "recovering"


VALID_TRANSITIONS = {
    RuntimeLifecycle.UNINITIALIZED: [RuntimeLifecycle.INITIALIZING],
    RuntimeLifecycle.INITIALIZING: [RuntimeLifecycle.INITIALIZED],
    RuntimeLifecycle.INITIALIZED: [RuntimeLifecycle.REGISTERING_PLUGINS],
    RuntimeLifecycle.REGISTERING_PLUGINS: [
        RuntimeLifecycle.PLUGINS_REGISTERED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.PLUGINS_REGISTERED: [
        RuntimeLifecycle.VALIDATING_CONTRACTS,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.VALIDATING_CONTRACTS: [
        RuntimeLifecycle.CONTRACTS_VALIDATED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.CONTRACTS_VALIDATED: [
        RuntimeLifecycle.STARTING_PROVIDERS,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.STARTING_PROVIDERS: [
        RuntimeLifecycle.PROVIDERS_STARTED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.PROVIDERS_STARTED: [
        RuntimeLifecycle.STARTING_AGENTS,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.STARTING_AGENTS: [
        RuntimeLifecycle.AGENTS_STARTED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.AGENTS_STARTED: [RuntimeLifecycle.RUNNING],
    RuntimeLifecycle.RUNNING: [
        RuntimeLifecycle.SHUTTING_DOWN,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.SHUTTING_DOWN: [
        RuntimeLifecycle.STOPPED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.STOPPED: [
        RuntimeLifecycle.UNINITIALIZED,
        RuntimeLifecycle.RECOVERING,
    ],
    RuntimeLifecycle.RECOVERING: [
        RuntimeLifecycle.INITIALIZING,
        RuntimeLifecycle.REGISTERING_PLUGINS,
        RuntimeLifecycle.VALIDATING_CONTRACTS,
        RuntimeLifecycle.STARTING_PROVIDERS,
        RuntimeLifecycle.STARTING_AGENTS,
        RuntimeLifecycle.RUNNING,
    ],
}


class LifecycleError(Exception):
    pass


def transition_lifecycle(current: RuntimeLifecycle, target: RuntimeLifecycle) -> RuntimeLifecycle:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise LifecycleError(
            f"Cannot transition from {current.value} to {target.value}. Allowed: {[s.value for s in allowed]}"
        )
    return target
