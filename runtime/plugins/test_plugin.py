"""Minimal test plugin for Runtime integration testing."""

from runtime.plugins.base import Plugin


class MinimalTestPlugin(Plugin):
    name = "minimal_test"
    version = "0.1.0"
    description = "Minimal test plugin for Runtime integration testing"
    runtime_version_required = ">=0.1.0"
