"""Tests for dashboard.config.config — covering uncovered lines (14-18)."""

from __future__ import annotations

from unittest.mock import mock_open, patch


class TestLoadDataConfig:
    """Cover _load_data_config (lines 14-18)."""

    def _clear_cache(self):
        from dashboard.config import config as cfg

        cfg._CONFIG_CACHE = None

    def test_load_data_config_returns_dict(self):
        self._clear_cache()
        from dashboard.config.config import _load_data_config

        with (
            patch("builtins.open", mock_open(read_data="key: value")),
            patch("dashboard.config.config.yaml.safe_load", return_value={"key": "value"}),
        ):
            result = _load_data_config()
            assert result == {"key": "value"}

    def test_load_data_config_cached(self):
        from dashboard.config.config import _load_data_config

        self._clear_cache()
        from dashboard.config import config as cfg

        cfg._CONFIG_CACHE = {"cached": "data"}
        result = _load_data_config()
        assert result == {"cached": "data"}

    def test_load_data_config_file_not_found(self):
        self._clear_cache()
        from dashboard.config.config import _load_data_config

        with patch("builtins.open", side_effect=FileNotFoundError):
            import pytest

            with pytest.raises(FileNotFoundError):
                _load_data_config()

    def test_load_data_config_yaml_error(self):
        self._clear_cache()
        from dashboard.config.config import _load_data_config

        with (
            patch("builtins.open", mock_open(read_data="invalid: yaml: :")),
            patch("dashboard.config.config.yaml.safe_load", side_effect=Exception("YAML error")),
        ):
            import pytest

            with pytest.raises(Exception, match="YAML error"):
                _load_data_config()
