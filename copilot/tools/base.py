from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]: ...

    @abstractmethod
    def validate(self, **kwargs: Any) -> tuple[bool, str]: ...

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...

    @abstractmethod
    def health_check(self) -> tuple[bool, str]: ...
