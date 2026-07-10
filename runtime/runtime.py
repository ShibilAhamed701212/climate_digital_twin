from __future__ import annotations

import logging
from typing import Any

from runtime.agents.base import Agent
from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.lifecycle import RuntimeLifecycle
from runtime.models.events import Event
from runtime.models.runtime import RuntimeContext, RuntimeResult
from runtime.pipeline.engine import PipelineEngine
from runtime.plugins.base import Plugin
from runtime.plugins.loader import PluginLoader
from runtime.providers.echo import EchoProvider
from runtime.providers.registry import ProviderRegistry
from runtime.workflow.base import WorkflowDefinition
from runtime.workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Domain-agnostic AI Runtime orchestrator."""

    def __init__(self):
        self.lifecycle = RuntimeLifecycle.UNINITIALIZED
        self.blackboard: Blackboard | None = None
        self.event_bus: EventBus | None = None
        self.provider_registry: ProviderRegistry | None = None
        self.capability_router: CapabilityRouter | None = None
        self.workflow_engine: WorkflowEngine | None = None
        self.pipeline_engine: PipelineEngine | None = None
        self.plugin_loader: PluginLoader | None = None
        self.plugins: dict[str, Plugin] = {}
        self.agents: dict[str, Agent] = {}
        self.metrics: dict[str, Any] = {"requests_processed": 0, "errors": 0}

    async def initialize(self) -> None:
        self.lifecycle = RuntimeLifecycle.INITIALIZING
        logger.info("Runtime initializing...")
        self.blackboard = Blackboard()
        self.event_bus = EventBus()
        self.provider_registry = ProviderRegistry()
        self.capability_router = CapabilityRouter()
        self.plugin_loader = PluginLoader()
        self.provider_registry.register("runtime.echo", EchoProvider())
        self.workflow_engine = WorkflowEngine(
            provider_registry=self.provider_registry,
            capability_router=self.capability_router,
            blackboard=self.blackboard,
            event_bus=self.event_bus,
        )
        self.pipeline_engine = PipelineEngine()
        self.lifecycle = RuntimeLifecycle.INITIALIZED
        self.lifecycle = RuntimeLifecycle.REGISTERING_PLUGINS
        self.lifecycle = RuntimeLifecycle.PLUGINS_REGISTERED
        self.lifecycle = RuntimeLifecycle.VALIDATING_CONTRACTS
        self.lifecycle = RuntimeLifecycle.CONTRACTS_VALIDATED
        self.lifecycle = RuntimeLifecycle.STARTING_PROVIDERS
        self.lifecycle = RuntimeLifecycle.PROVIDERS_STARTED
        self.lifecycle = RuntimeLifecycle.STARTING_AGENTS
        self.lifecycle = RuntimeLifecycle.AGENTS_STARTED
        self.lifecycle = RuntimeLifecycle.RUNNING
        self.event_bus.publish(
            Event(
                type="runtime.started",
                data={"version": "0.1.0"},
                source="runtime",
                trace_id="system",
            )
        )
        logger.info("Runtime initialized and running.")

    def load_plugin(self, plugin: Plugin) -> None:
        self.plugin_loader.validate_manifest(plugin.manifest)
        plugin_id = plugin.manifest.plugin_id
        if plugin_id in self.plugins:
            raise ValueError(f"Plugin '{plugin_id}' already loaded")
        plugin.register_capabilities(self.capability_router)
        plugin.register_providers(self.provider_registry)
        plugin.register_events(self.event_bus)
        plugin.register_workflows(self.workflow_engine)
        plugin.register_configuration(self)
        plugin.register_agents(self)
        plugin.register_pipelines(self)
        self.plugins[plugin_id] = plugin
        logger.info(
            f"Plugin loaded: {plugin.manifest.plugin_name} v{plugin.manifest.version}"
        )

    def register_agent(self, agent: Agent) -> None:
        if agent.name in self.agents:
            logger.warning(f"Agent '{agent.name}' already registered, overwriting")
        self.agents[agent.name] = agent

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        self.workflow_engine.register(workflow)

    def register_pipeline(self, pipeline) -> None:
        self.pipeline_engine.register(pipeline)

    async def execute_workflow(
        self, trigger: str, context: RuntimeContext
    ) -> RuntimeResult:
        try:
            context.log_stage("workflow.lookup", {"trigger": trigger})
            workflow = self.workflow_engine.find_workflow(trigger)
            if workflow is None:
                return RuntimeResult(
                    success=False,
                    error=f"No workflow found for trigger '{trigger}'",
                    trace_id=context.trace_id,
                    trace_log=context.trace_log,
                )
            context.log_stage("workflow.execute", {"workflow_id": workflow.id})
            result_data = await self.workflow_engine.execute(workflow, context)
            context.log_stage(
                "workflow.complete", {"steps_completed": list(result_data.keys())}
            )
            return RuntimeResult(
                success=True,
                response=result_data,
                data=result_data,
                latency_ms=context.elapsed_ms(),
                trace_id=context.trace_id,
                trace_log=context.trace_log,
            )
        except Exception as e:
            context.log_stage("workflow.error", {"error": str(e)})
            logger.exception(f"Workflow execution failed: {e}")
            self.metrics["errors"] += 1
            return RuntimeResult(
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
                trace_id=context.trace_id,
                trace_log=context.trace_log,
            )

    async def process(self, trigger: str, context: RuntimeContext) -> RuntimeResult:
        if self.lifecycle != RuntimeLifecycle.RUNNING:
            return RuntimeResult(
                success=False,
                error=f"Runtime is {self.lifecycle.value}, not running",
                trace_id=context.trace_id,
            )
        self.metrics["requests_processed"] += 1
        context.log_stage("runtime.process", {"trigger": trigger})
        self.event_bus.publish(
            Event(
                type="request.received",
                data={"trigger": trigger},
                source="runtime",
                trace_id=context.trace_id,
            )
        )

        # Phase 2: Try pipeline execution first (cognitive pipeline)
        pipeline = self.pipeline_engine.find(trigger) if self.pipeline_engine else None
        if pipeline:
            context.log_stage(
                "runtime.pipeline",
                {"pipeline_id": pipeline.id, "stages": len(pipeline.stages)},
            )
            from runtime.models.pipeline import ExecutionContext

            ectx = ExecutionContext(
                runtime_context=context,
                blackboard=self.blackboard,
                event_bus=self.event_bus,
                provider_registry=self.provider_registry,
                capability_router=self.capability_router,
            )
            ectx = await self.pipeline_engine.execute(pipeline, ectx)

            response = ectx.stage_outputs.get("response", "")
            result_data = {
                "response": response,
                "intent": ectx.stage_outputs.get("intent", "unknown"),
                "citations": ectx.stage_outputs.get("citations", []),
                "trace": ectx.trace,
                "metrics": ectx.metrics,
                "stage_outputs": dict(ectx.stage_outputs),
            }

            self.event_bus.publish(
                Event(
                    type="pipeline.completed",
                    data={"pipeline_id": pipeline.id, "success": len(ectx.errors) == 0},
                    source="runtime",
                    trace_id=context.trace_id,
                )
            )

            return RuntimeResult(
                success=len(ectx.errors) == 0,
                response=response,
                data=result_data,
                latency_ms=context.elapsed_ms(),
                trace_id=context.trace_id,
                trace_log=context.trace_log,
            )

        # Fallback to workflow-based execution (Phase 1 backward compat)
        result = await self.execute_workflow(trigger, context)
        self.event_bus.publish(
            Event(
                type="request.completed",
                data={
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "trigger": trigger,
                },
                source="runtime",
                trace_id=context.trace_id,
            )
        )
        return result

    async def shutdown(self) -> None:
        logger.info("Runtime shutting down...")
        self.lifecycle = RuntimeLifecycle.SHUTTING_DOWN
        self.event_bus.publish(
            Event(
                type="runtime.stopping",
                data={"metrics": self.metrics},
                source="runtime",
                trace_id="system",
            )
        )
        self.agents.clear()
        self.plugins.clear()
        self.lifecycle = RuntimeLifecycle.STOPPED
        logger.info("Runtime stopped.")

    async def recover(self) -> None:
        logger.info("Runtime recovering...")
        self.lifecycle = RuntimeLifecycle.RECOVERING
        self.metrics["errors"] = 0
        if self.lifecycle == RuntimeLifecycle.STOPPED:
            await self.initialize()
