from __future__ import annotations

from typing import Any

from runtime.capabilities.base import CapabilityType
from runtime.providers.base import Provider
from runtime.providers.registry import ProviderRegistry


class CapabilityRouter:
    """Routes requests to capabilities and selects providers."""

    def __init__(self):
        self._capabilities: dict[str, list[CapabilityType]] = {}

    def register(self, capability: CapabilityType) -> None:
        if capability.name not in self._capabilities:
            self._capabilities[capability.name] = []
        self._capabilities[capability.name].append(capability)

    def resolve(self, name: str) -> CapabilityType | None:
        versions = self._capabilities.get(name, [])
        return versions[-1] if versions else None

    def select_provider(
        self,
        capability: str,
        registry: ProviderRegistry,
        constraints: dict[str, Any] | None = None,
    ) -> Provider | None:
        return registry.get_best(capability, constraints)

    def validate_contract(
        self, capability: str, input_data: dict[str, Any], output_data: dict[str, Any]
    ) -> bool:
        cap = self.resolve(capability)
        if not cap:
            return False
        try:
            import jsonschema

            jsonschema.validate(input_data, cap.input_schema)
            jsonschema.validate(output_data, cap.output_schema)
            return True
        except ImportError:
            return True
        except jsonschema.ValidationError:
            return False

    def compose(self, name: str, visited: set[str] | None = None) -> list[str]:
        """Resolve a capability name into an ordered dependency chain.

        Returns a list of capability names in execution order.
        Lightweight — no full workflow planner.
        """
        if visited is None:
            visited = set()
        if name in visited:
            return []
        visited.add(name)

        cap = self.resolve(name)
        if cap is None:
            return [name]

        chain: list[str] = []
        for dep in cap.dependencies:
            dep_chain = self.compose(dep, visited)
            for d in dep_chain:
                if d not in chain:
                    chain.append(d)

        if name not in chain:
            chain.append(name)

        return chain

    def resolve_chain(
        self, name: str, registry: ProviderRegistry
    ) -> list[tuple[str, object | None]]:
        """Resolve a capability chain into (capability, provider) pairs.

        Lightweight — uses compose() to build the chain and select_provider for each.
        """
        chain = self.compose(name)
        result: list[tuple[str, object | None]] = []
        for cap_name in chain:
            provider = self.select_provider(cap_name, registry)
            result.append((cap_name, provider))
        return result

    def list_capabilities(self) -> dict[str, str]:
        return {
            name: versions[-1].version for name, versions in self._capabilities.items()
        }
