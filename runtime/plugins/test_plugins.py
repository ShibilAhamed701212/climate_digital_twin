import pytest

from runtime.models.plugin import PluginManifest
from runtime.plugins.loader import PluginLoader, PluginValidationError
from runtime.plugins.test_plugin import MinimalTestPlugin


class TestPluginBase:
    def test_minimal_plugin(self):
        p = MinimalTestPlugin()
        assert p.name == "minimal_test"
        assert p.version == "0.1.0"

    def test_manifest(self):
        p = MinimalTestPlugin()
        m = p.manifest
        assert m.plugin_id == "minimal_test"
        assert m.version == "0.1.0"


class TestPluginLoader:
    def test_validate_manifest_valid(self):
        PluginLoader().validate_manifest(
            PluginManifest(
                plugin_id="valid",
                plugin_name="Valid",
                version="1.0.0",
                runtime_version_required=">=0.1.0",
                description="",
            )
        )

    def test_validate_manifest_none(self):
        with pytest.raises(PluginValidationError):
            PluginLoader().validate_manifest(None)

    def test_validate_manifest_missing_id(self):
        with pytest.raises(PluginValidationError):
            PluginLoader().validate_manifest(
                PluginManifest(
                    plugin_id="",
                    plugin_name="n",
                    version="1.0.0",
                    runtime_version_required=">=0.1.0",
                    description="",
                )
            )

    def test_validate_manifest_missing_name(self):
        with pytest.raises(PluginValidationError):
            PluginLoader().validate_manifest(
                PluginManifest(
                    plugin_id="n",
                    plugin_name="",
                    version="1.0.0",
                    runtime_version_required=">=0.1.0",
                    description="",
                )
            )

    def test_validate_manifest_missing_version(self):
        with pytest.raises(PluginValidationError):
            PluginLoader().validate_manifest(
                PluginManifest(
                    plugin_id="n",
                    plugin_name="n",
                    version="",
                    runtime_version_required=">=0.1.0",
                    description="",
                )
            )

    def test_validate_manifest_bad_version(self):
        with pytest.raises(PluginValidationError):
            PluginLoader().validate_manifest(
                PluginManifest(
                    plugin_id="n",
                    plugin_name="n",
                    version="bad",
                    runtime_version_required=">=0.1.0",
                    description="",
                )
            )

    def test_validate_manifest_incompatible_runtime(self):
        loader = PluginLoader(runtime_version="0.1.0")
        with pytest.raises(PluginValidationError):
            loader.validate_manifest(
                PluginManifest(
                    plugin_id="n",
                    plugin_name="n",
                    version="1.0.0",
                    runtime_version_required=">=2.0.0",
                    description="",
                )
            )

    def test_load_plugin(self):
        p = PluginLoader(runtime_version="0.1.0").load_plugin(MinimalTestPlugin)
        assert p.name == "minimal_test"

    def test_discover_no_paths(self):
        assert PluginLoader().discover() == []
