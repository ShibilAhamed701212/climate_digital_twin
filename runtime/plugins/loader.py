from __future__ import annotations

import re

from runtime.models.plugin import PluginManifest
from runtime.plugins.base import Plugin
from runtime.version import __version__ as RUNTIME_VERSION  # noqa: N812

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class PluginValidationError(Exception):
    pass


def _parse_version(v: str) -> tuple[int, int, int]:
    parts = v.split(".")
    return (
        int(parts[0]),
        int(parts[1]) if len(parts) > 1 else 0,
        int(parts[2]) if len(parts) > 2 else 0,
    )


def _satisfies_version(required: str, runtime_ver: str) -> bool:
    required = required.strip()
    if required.startswith(">="):
        return _parse_version(runtime_ver) >= _parse_version(required[2:].strip())
    elif required.startswith("=="):
        return _parse_version(runtime_ver) == _parse_version(required[2:].strip())
    return True


class PluginLoader:
    def __init__(self, plugin_paths: list[str] | None = None, runtime_version: str | None = None):
        self.plugin_paths = plugin_paths or []
        self.runtime_version = runtime_version or RUNTIME_VERSION

    def discover(self) -> list[type[Plugin]]:
        return []

    def validate_manifest(self, manifest: PluginManifest | None) -> None:
        if manifest is None:
            raise PluginValidationError("Plugin manifest is None")
        errors = []
        if not manifest.plugin_id:
            errors.append("plugin_id is required")
        if not manifest.plugin_name:
            errors.append("plugin_name is required")
        if not manifest.version:
            errors.append("version is required")
        elif not SEMVER_RE.match(manifest.version):
            errors.append(f"version '{manifest.version}' is not valid semver (X.Y.Z)")
        if not manifest.runtime_version_required:
            errors.append("runtime_version_required is required")
        if (
            manifest.runtime_version_required
            and self.runtime_version
            and not _satisfies_version(manifest.runtime_version_required, self.runtime_version)
        ):
            errors.append(
                f"Runtime v{self.runtime_version} does not satisfy '{manifest.runtime_version_required}'"
            )
        if errors:
            raise PluginValidationError("; ".join(errors))

    def load_plugin(self, plugin_cls: type[Plugin]) -> Plugin:
        plugin = plugin_cls()
        self.validate_manifest(plugin.manifest)
        return plugin
