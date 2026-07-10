from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginManifest:
    """Declared metadata for a Runtime plugin.

    The Runtime validates this manifest before loading the plugin.
    All fields are required unless marked optional.
    """

    plugin_id: str
    plugin_name: str
    version: str
    runtime_version_required: str  # semver range, e.g. ">=0.1.0"
    description: str
    capabilities: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    configuration_schema: dict[str, Any] | None = None
