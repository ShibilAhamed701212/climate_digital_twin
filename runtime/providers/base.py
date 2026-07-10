from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from runtime.models.provider import ProviderHealth, ProviderRequest, ProviderResult


class Provider(ABC):
    """Abstract provider. All domain providers implement this interface.

    A provider implements a single capability.
    Multiple providers can implement the same capability.
    """

    provider_id: str = ""
    capability: str = ""
    config: dict[str, Any] = {}

    @abstractmethod
    async def execute(self, request: ProviderRequest) -> ProviderResult: ...

    @abstractmethod
    def health(self) -> ProviderHealth: ...

    @property
    def deterministic(self) -> bool:
        return True
