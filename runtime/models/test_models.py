"""Tests for runtime data models."""

import json

from runtime.models.agent import AgentParams, AgentResult
from runtime.models.blackboard import BBEntry
from runtime.models.capability import CapabilityType
from runtime.models.events import Event
from runtime.models.plugin import PluginManifest
from runtime.models.provider import ProviderHealth, ProviderRequest, ProviderResult
from runtime.models.runtime import RuntimeContext, RuntimeResult
from runtime.models.workflow import WorkflowDefinition, WorkflowStep


class TestEvent:
    def test_create(self):
        e = Event(type="test.event", data={"key": "val"}, source="test", trace_id="abc")
        assert e.type == "test.event"
        assert e.data["key"] == "val"
        assert e.source == "test"
        assert e.trace_id == "abc"
        assert e.timestamp > 0


class TestBBEntry:
    def test_create(self):
        e = BBEntry(
            key="test.key", value={"nested": True}, agent="test-agent", version=1
        )
        assert e.key == "test.key"
        assert e.value["nested"] is True
        assert e.agent == "test-agent"
        assert e.version == 1

    def test_with_parent(self):
        child = BBEntry(key="k", value="v", agent="a", version=2, parent_version=1)
        assert child.parent_version == 1


class TestProviderModels:
    def test_request(self):
        ctx = RuntimeContext(trace_id="t1")
        req = ProviderRequest(capability="echo", params={"msg": "hello"}, context=ctx)
        assert req.capability == "echo"
        assert req.params["msg"] == "hello"

    def test_result_success(self):
        r = ProviderResult(success=True, data={"result": 42}, confidence=0.95)
        assert r.success is True
        assert r.data["result"] == 42
        assert r.confidence == 0.95

    def test_result_error(self):
        r = ProviderResult(success=False, error="Something broke")
        assert r.success is False
        assert r.error == "Something broke"

    def test_health_ok(self):
        h = ProviderHealth(ok=True, version="1.0")
        assert h.ok is True
        assert h.version == "1.0"

    def test_health_fail(self):
        h = ProviderHealth(ok=False, message="Down")
        assert h.ok is False


class TestAgentModels:
    def test_params(self):
        ctx = RuntimeContext(trace_id="t1")
        p = AgentParams(task="test", params={"x": 1}, context=ctx)
        assert p.task == "test"

    def test_result(self):
        r = AgentResult(success=True, data=[1, 2, 3])
        assert r.success is True
        assert r.data == [1, 2, 3]


class TestCapabilityType:
    def test_create(self):
        ct = CapabilityType(
            name="test.capability",
            description="A test capability",
            version="1.0.0",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert ct.name == "test.capability"
        assert ct.version == "1.0.0"
        assert ct.deterministic_possible is True

    def test_default_policies(self):
        ct = CapabilityType(
            name="c",
            description="d",
            version="1",
            input_schema={},
            output_schema={},
        )
        assert ct.timeout_policy.default_ms == 30000
        assert ct.retry_policy.max_retries == 2
        assert ct.cache_policy.ttl_seconds == 60


class TestPluginManifest:
    def test_minimal(self):
        m = PluginManifest(
            plugin_id="test.plugin",
            plugin_name="Test Plugin",
            version="0.1.0",
            runtime_version_required=">=0.1.0",
            description="A test plugin",
        )
        assert m.plugin_id == "test.plugin"
        assert m.capabilities == []

    def test_full(self):
        m = PluginManifest(
            plugin_id="full.plugin",
            plugin_name="Full",
            version="1.0.0",
            runtime_version_required=">=0.1.0",
            description="Full test",
            capabilities=["cap1", "cap2"],
            providers=["prov1"],
            workflows=["wf1"],
            permissions=["read"],
            dependencies=["other-plugin"],
            configuration_schema={"type": "object"},
        )
        assert len(m.capabilities) == 2
        assert m.configuration_schema is not None


class TestWorkflowModels:
    def test_step(self):
        s = WorkflowStep(id="step1", capability="echo", params={"msg": "hello"})
        assert s.id == "step1"
        assert s.on_failure == "abort"

    def test_step_with_deps(self):
        s = WorkflowStep(
            id="step2", capability="compute", params={"x": 1}, depends_on=["step1"]
        )
        assert "step1" in s.depends_on

    def test_definition(self):
        s = WorkflowStep(id="s1", capability="echo", params={})
        wf = WorkflowDefinition(
            id="test.wf",
            name="Test Workflow",
            version="1.0.0",
            description="A test workflow",
            triggers=["test"],
            steps=[s],
        )
        assert wf.id == "test.wf"
        assert len(wf.steps) == 1


class TestRuntimeContext:
    def test_create(self):
        ctx = RuntimeContext(trace_id="abc123")
        assert ctx.trace_id == "abc123"
        assert ctx.elapsed_ms() >= 0

    def test_log_stage(self):
        ctx = RuntimeContext(trace_id="t1")
        ctx.log_stage("init", {"msg": "starting"})
        assert len(ctx.trace_log) == 1
        assert ctx.trace_log[0]["stage"] == "init"

    def test_default_trace_id(self):
        ctx = RuntimeContext()
        assert len(ctx.trace_id) == 16


class TestRuntimeResult:
    def test_create(self):
        r = RuntimeResult(success=True, response="OK", trace_id="abc")
        assert r.success is True
        assert r.response == "OK"


class TestModelJsonSerialization:
    def test_event_json(self):
        e = Event(type="t", data={"k": "v"}, source="s", trace_id="tid")
        d = {"type": e.type, "data": e.data, "source": e.source, "trace_id": e.trace_id}
        j = json.dumps(d)
        assert '"k": "v"' in j
