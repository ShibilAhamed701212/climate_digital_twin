from pathlib import Path
from unittest.mock import patch

import pytest

import simulator.configs.bhai_config as bc


class TestConfigure:
    def setup_method(self):
        bc._config = None

    def test_configure_updates_config(self):
        result = bc.configure(log_level="DEBUG")
        assert result.log_level == "DEBUG"
        assert isinstance(result, bc.ClimateDTConfig)

    def test_configure_returns_config(self):
        result = bc.configure(observations_dir="new_obs")
        assert result.observations_dir == Path("new_obs")

    def test_configure_converts_dir_string_to_path(self):
        result = bc.configure(observations_dir="/some/path")
        assert isinstance(result.observations_dir, Path)

    def test_configure_keeps_path_unchanged(self):
        result = bc.configure(data_dir=Path("/custom/data"))
        assert result.data_dir == Path("/custom/data")

    def test_configure_unknown_key_raises(self):
        with pytest.raises(TypeError, match="Unknown configuration option"):
            bc.configure(nonexistent="value")

    def test_configure_unknown_key_raises_non_dir(self):
        with pytest.raises(TypeError, match="Unknown configuration option"):
            bc.configure(bad_key=123)


class TestGetDataDir:
    def setup_method(self):
        bc._config = None

    def test_get_data_dir_returns_path(self, tmp_path):
        cfg = bc.ClimateDTConfig()
        cfg.data_dir = tmp_path
        with patch.object(bc, "get_config", return_value=cfg):
            result = bc.get_data_dir()
            assert isinstance(result, Path)
            assert result.exists()

    def test_get_data_dir_creates_directory(self, tmp_path):
        target = tmp_path / "nested" / "data"
        cfg = bc.ClimateDTConfig()
        cfg.data_dir = target
        with patch.object(bc, "get_config", return_value=cfg):
            result = bc.get_data_dir()
            assert result.exists()


class TestResolveSubdir:
    def setup_method(self):
        bc._config = None

    def test_resolve_subdir_returns_path(self, tmp_path):
        cfg = bc.ClimateDTConfig()
        cfg.data_dir = tmp_path
        with patch.object(bc, "get_config", return_value=cfg):
            result = bc.resolve_subdir("subtest")
            assert isinstance(result, Path)
            assert result.exists()

    def test_resolve_subdir_creates_nested(self, tmp_path):
        cfg = bc.ClimateDTConfig()
        cfg.data_dir = tmp_path
        with patch.object(bc, "get_config", return_value=cfg):
            result = bc.resolve_subdir("a/b/c")
            assert result.exists()
