from __future__ import annotations

import asyncio
from typing import Any

from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.events import Event
from runtime.models.provider import ProviderRequest, ProviderResult
from runtime.models.runtime import RuntimeContext
from runtime.providers.registry import ProviderRegistry
from runtime.workflow.base import WorkflowDefinition


class WorkflowEngine:
    """Executes declarative workflow DAGs."""

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        capability_router: CapabilityRouter,
        blackboard: Blackboard,
        event_bus: EventBus,
    ):
        self._workflows: dict[str, WorkflowDefinition] = {}
        self.provider_registry = provider_registry
        self.capability_router = capability_router
        self.blackboard = blackboard
        self.event_bus = event_bus

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.id] = workflow

    def find_workflow(self, trigger: str) -> WorkflowDefinition | None:
        for wf in self._workflows.values():
            if trigger in wf.triggers:
                return wf
        return None

    async def execute(
        self, workflow: WorkflowDefinition, context: RuntimeContext
    ) -> dict[str, ProviderResult]:
        steps = {s.id: s for s in workflow.steps}
        completed: dict[str, ProviderResult] = {}
        remaining = set(steps.keys())

        while remaining:
            ready = [
                sid for sid in remaining if all(dep in completed for dep in steps[sid].depends_on)
            ]
            if not ready:
                raise RuntimeError(
                    f"Deadlock in workflow '{workflow.id}': remaining steps {remaining}"
                )
            results = await asyncio.gather(
                *[self._execute_step(steps[sid], context) for sid in ready],
                return_exceptions=True,
            )
            for sid, result in zip(ready, results, strict=True):
                if isinstance(result, Exception):
                    raise result
                completed[sid] = result
                remaining.remove(sid)
                self.event_bus.publish(
                    Event(
                        type="workflow.step.completed",
                        data={"workflow_id": workflow.id, "step_id": sid},
                        source="workflow_engine",
                        trace_id=context.trace_id,
                    )
                )

        self.event_bus.publish(
            Event(
                type="workflow.completed",
                data={"workflow_id": workflow.id},
                source="workflow_engine",
                trace_id=context.trace_id,
            )
        )
        return completed

    async def _execute_step(self, step: Any, context: RuntimeContext) -> ProviderResult:
        provider = self.capability_router.select_provider(step.capability, self.provider_registry)
        if provider is None:
            raise ValueError(
                f"No provider found for capability '{step.capability}' (step '{step.id}')"
            )
        try:
            return await provider.execute(
                ProviderRequest(
                    capability=step.capability,
                    params=step.params,
                    context=context,
                    timeout_ms=step.timeout_ms,
                )
            )
        except Exception as e:
            if step.on_failure == "skip":
                return ProviderResult(success=False, error=str(e))
            raise

    def list_workflows(self) -> dict[str, str]:
        return {wf.id: wf.version for wf in self._workflows.values()}
