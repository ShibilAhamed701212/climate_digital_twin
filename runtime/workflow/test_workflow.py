import pytest

from runtime.blackboard import Blackboard
from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.runtime import RuntimeContext
from runtime.models.workflow import WorkflowDefinition, WorkflowStep
from runtime.providers.echo import EchoProvider
from runtime.providers.registry import ProviderRegistry
from runtime.workflow.engine import WorkflowEngine


@pytest.fixture
def engine():
    registry = ProviderRegistry()
    registry.register("runtime.echo", EchoProvider())
    router = CapabilityRouter()
    return WorkflowEngine(
        provider_registry=registry,
        capability_router=router,
        blackboard=Blackboard(),
        event_bus=EventBus(),
    )


class TestWorkflowEngine:
    def test_register_and_find(self, engine):
        s = WorkflowStep(id="s1", capability="runtime.echo", params={"msg": "hello"})
        wf = WorkflowDefinition(
            id="test.wf",
            name="Test",
            version="1.0",
            description="",
            triggers=["t"],
            steps=[s],
        )
        engine.register(wf)
        assert engine.find_workflow("t") is not None
        assert engine.find_workflow("t").id == "test.wf"

    def test_find_nonexistent(self, engine):
        assert engine.find_workflow("nonexistent") is None

    @pytest.mark.asyncio
    async def test_execute_single_step(self, engine):
        s = WorkflowStep(id="s1", capability="runtime.echo", params={"msg": "hello"})
        wf = WorkflowDefinition(
            id="e.wf",
            name="Echo",
            version="1.0",
            description="",
            triggers=["e"],
            steps=[s],
        )
        ctx = RuntimeContext(trace_id="t1")
        result = await engine.execute(wf, ctx)
        assert result["s1"].success is True
        assert result["s1"].data["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_execute_sequential(self, engine):
        s1 = WorkflowStep(id="a", capability="runtime.echo", params={"v": 1})
        s2 = WorkflowStep(
            id="b", capability="runtime.echo", params={"v": 2}, depends_on=["a"]
        )
        wf = WorkflowDefinition(
            id="s.wf",
            name="Seq",
            version="1.0",
            description="",
            triggers=["s"],
            steps=[s1, s2],
        )
        ctx = RuntimeContext(trace_id="t2")
        result = await engine.execute(wf, ctx)
        assert result["a"].success is True
        assert result["b"].success is True

    @pytest.mark.asyncio
    async def test_execute_parallel(self, engine):
        s1 = WorkflowStep(id="p1", capability="runtime.echo", params={"id": 1})
        s2 = WorkflowStep(id="p2", capability="runtime.echo", params={"id": 2})
        wf = WorkflowDefinition(
            id="p.wf",
            name="Par",
            version="1.0",
            description="",
            triggers=["p"],
            steps=[s1, s2],
        )
        ctx = RuntimeContext(trace_id="t3")
        result = await engine.execute(wf, ctx)
        assert result["p1"].data["id"] == 1
        assert result["p2"].data["id"] == 2

    @pytest.mark.asyncio
    async def test_execute_deadlock(self, engine):
        s1 = WorkflowStep(
            id="a", capability="runtime.echo", params={}, depends_on=["b"]
        )
        s2 = WorkflowStep(
            id="b", capability="runtime.echo", params={}, depends_on=["a"]
        )
        wf = WorkflowDefinition(
            id="d.wf",
            name="Dead",
            version="1.0",
            description="",
            triggers=["d"],
            steps=[s1, s2],
        )
        ctx = RuntimeContext(trace_id="t4")
        with pytest.raises(RuntimeError, match="Deadlock"):
            await engine.execute(wf, ctx)

    @pytest.mark.asyncio
    async def test_missing_capability(self, engine):
        s = WorkflowStep(id="s1", capability="nonexistent", params={})
        wf = WorkflowDefinition(
            id="b.wf",
            name="Bad",
            version="1.0",
            description="",
            triggers=["b"],
            steps=[s],
        )
        ctx = RuntimeContext(trace_id="t5")
        with pytest.raises(ValueError):
            await engine.execute(wf, ctx)

    def test_list_workflows(self, engine):
        s = WorkflowStep(id="s1", capability="echo", params={})
        wf = WorkflowDefinition(
            id="l.wf",
            name="List",
            version="2.0",
            description="",
            triggers=["l"],
            steps=[s],
        )
        engine.register(wf)
        wfs = engine.list_workflows()
        assert "l.wf" in wfs
        assert wfs["l.wf"] == "2.0"
