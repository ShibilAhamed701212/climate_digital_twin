import pytest

from runtime.agents.base import Agent
from runtime.blackboard import Blackboard
from runtime.models.agent import AgentParams, AgentResult
from runtime.models.runtime import RuntimeContext


class TestAgentBase:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            Agent()

    @pytest.mark.asyncio
    async def test_minimal_agent(self):
        class EchoAgent(Agent):
            name = "echo"
            description = "Echoes input"

            async def run(self, params, _blackboard):
                return AgentResult(success=True, data=params.params)

        agent = EchoAgent()
        assert agent.name == "echo"
        ctx = RuntimeContext(trace_id="t1")
        p = AgentParams(task="echo", params={"msg": "hi"}, context=ctx)
        result = await agent.run(p, Blackboard())
        assert result.success is True
        assert result.data["msg"] == "hi"

    @pytest.mark.asyncio
    async def test_agent_error(self):
        class FailAgent(Agent):
            name = "fail"
            description = "Always fails"

            async def run(self, _params, _blackboard):
                return AgentResult(success=False, error="fail")

        agent = FailAgent()
        ctx = RuntimeContext(trace_id="t1")
        p = AgentParams(task="f", params={}, context=ctx)
        result = await agent.run(p, Blackboard())
        assert result.success is False
        assert result.error == "fail"
