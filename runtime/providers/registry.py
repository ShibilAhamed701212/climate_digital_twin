from __future__ import annotations

from collections import defaultdict
from typing import Any

from runtime.providers.base import Provider


class ProviderRegistry:
    """Registry of all providers, organized by capability."""

    def __init__(self):
        self._providers: dict[str, list[Provider]] = defaultdict(list)

    def register(self, capability: str, provider: Provider) -> None:
        self._providers[capability].append(provider)

    def get_best(
        self, capability: str, constraints: dict[str, Any] | None = None
    ) -> Provider | None:
        providers = self._providers.get(capability, [])
        if not providers:
            return None
        constraints = constraints or {}
        if constraints.get("allow_deterministic", True):
            det = [p for p in providers if p.deterministic]
            if det:
                return det[0]
        healthy = [p for p in providers if p.health().ok]
        return healthy[0] if healthy else providers[0]

    def all_for(self, capability: str) -> list[Provider]:
        return list(self._providers.get(capability, []))
