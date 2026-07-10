import pytest

from runtime.lifecycle import LifecycleError, RuntimeLifecycle, transition_lifecycle
from runtime.models.runtime import RuntimeContext
from runtime.models.workflow import WorkflowDefinition, WorkflowStep
from runtime.plugins.test_plugin import MinimalTestPlugin
from runtime.runtime import AgentRuntime


class TestLifecycle:
    def test_initial_state(self):
        rt = AgentRuntime()
        assert rt.lifecycle == RuntimeLifecycle.UNINITIALIZED

    def test_transition_valid(self):
        assert (
            transition_lifecycle(
                RuntimeLifecycle.UNINITIALIZED, RuntimeLifecycle.INITIALIZING
            )
            == RuntimeLifecycle.INITIALIZING
        )

    def test_transition_invalid(self):
        with pytest.raises(LifecycleError):
            transition_lifecycle(
                RuntimeLifecycle.UNINITIALIZED, RuntimeLifecycle.RUNNING
            )


class TestRuntime:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        rt = AgentRuntime()
        await rt.initialize()
        assert rt.lifecycle == RuntimeLifecycle.RUNNING
        assert rt.blackboard is not None
        await rt.shutdown()
        assert rt.lifecycle == RuntimeLifecycle.STOPPED

    @pytest.mark.asyncio
    async def test_load_plugin(self):
        rt = AgentRuntime()
        await rt.initialize()
        rt.load_plugin(MinimalTestPlugin())
        assert "minimal_test" in rt.plugins
        await rt.shutdown()

    @pytest.mark.asyncio
    async def test_minimal_workflow(self):
        rt = AgentRuntime()
        await rt.initialize()
        s = WorkflowStep(id="s1", capability="runtime.echo", params={"msg": "hello"})
        wf = WorkflowDefinition(
            id="test.wf",
            name="Test",
            version="1.0",
            description="",
            triggers=["t"],
            steps=[s],
        )
        rt.register_workflow(wf)
        ctx = RuntimeContext(trace_id="test")
        result = await rt.process("t", ctx)
        assert result.success is True
        assert result.data["s1"].data["msg"] == "hello"
        await rt.shutdown()

    @pytest.mark.asyncio
    async def test_process_no_workflow(self):
        rt = AgentRuntime()
        await rt.initialize()
        ctx = RuntimeContext(trace_id="no-wf")
        result = await rt.process("nonexistent", ctx)
        assert result.success is False
        await rt.shutdown()

    @pytest.mark.asyncio
    async def test_process_after_shutdown(self):
        rt = AgentRuntime()
        await rt.initialize()
        await rt.shutdown()
        ctx = RuntimeContext(trace_id="post")
        result = await rt.process("x", ctx)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_plugin_registers_workflow(self):
        """Plugin registers a workflow, runtime executes it."""
        from runtime.plugins.base import Plugin

        class WFPlugin(Plugin):
            name = "wf_plugin"
            version = "0.1.0"

            def register_workflows(self, engine):
                s = WorkflowStep(
                    id="p1", capability="runtime.echo", params={"from": "plugin"}
                )
                engine.register(
                    WorkflowDefinition(
                        id="plugin.wf",
                        name="Plugin WF",
                        version="1.0",
                        description="",
                        triggers=["p"],
                        steps=[s],
                    )
                )

        rt = AgentRuntime()
        await rt.initialize()
        rt.load_plugin(WFPlugin())
        ctx = RuntimeContext(trace_id="plugin")
        result = await rt.process("p", ctx)
        assert result.success is True
        await rt.shutdown()
