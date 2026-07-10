from __future__ import annotations

from abc import ABC, abstractmethod

from runtime.blackboard import Blackboard
from runtime.models.agent import AgentParams, AgentResult


class Agent(ABC):
    """Abstract agent. All domain agents implement this interface."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, params: AgentParams, blackboard: Blackboard) -> AgentResult: ...
