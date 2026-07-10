from __future__ import annotations

from abc import ABC
from typing import Any

from runtime.capabilities.router import CapabilityRouter
from runtime.event_bus import EventBus
from runtime.models.plugin import PluginManifest
from runtime.providers.registry import ProviderRegistry


class Plugin(ABC):  # noqa: B024
    """Abstract plugin. All domain plugins implement this interface."""

    name: str = ""
    version: str = ""
    description: str = ""
    runtime_version_required: str = ">=0.0.0"

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            plugin_id=self.name,
            plugin_name=self.name,
            version=self.version,
            runtime_version_required=self.runtime_version_required,
            description=self.description,
        )

    def register_capabilities(self, router: CapabilityRouter) -> None:  # noqa: B027
        pass

    def register_agents(self, runtime: Any) -> None:  # noqa: B027
        pass

    def register_providers(self, registry: ProviderRegistry) -> None:  # noqa: B027
        pass

    def register_events(self, bus: EventBus) -> None:  # noqa: B027
        pass

    def register_workflows(self, engine: Any) -> None:  # noqa: B027
        pass

    def register_configuration(self, runtime: Any) -> None:  # noqa: B027
        pass

    def register_pipelines(self, runtime: Any) -> None:  # noqa: B027
        """Register Cognitive Pipeline Definitions.

        Pipelines define the cognitive flow (intent -> plan -> execute -> respond -> verify).
        The Runtime executes pipeline stages without knowing what they do.
        """
        pass
