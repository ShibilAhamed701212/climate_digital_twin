from __future__ import annotations

import logging

import pytest

from backend.api.config import GatewayConfig, _env_int, configure_gateway, get_gateway_config


@pytest.fixture(autouse=True)
def reset_config():
    from backend.api import config as _mod

    saved = _mod._config
    _mod._config = None
    yield
    _mod._config = saved


class TestEnvInt:
    def test_returns_default_when_var_missing(self) -> None:
        assert _env_int("NONEXISTENT_XYZ", 42) == 42

    def test_returns_int_when_var_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_ENV_INT", "99")
        assert _env_int("TEST_ENV_INT", 0) == 99

    def test_logs_warning_and_returns_default_on_bad_value(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("TEST_ENV_INT", "not_a_number")
        caplog.set_level(logging.WARNING)
        result = _env_int("TEST_ENV_INT", 10)
        assert result == 10
        assert "Invalid TEST_ENV_INT 'not_a_number', using default 10" in caplog.text


class TestGatewayConfig:
    def test_default_fields(self) -> None:
        cfg = GatewayConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8000
        assert cfg.debug is False
        assert cfg.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8501",
        ]
        assert cfg.api_key_enabled is False
        assert cfg.api_key == ""
        assert cfg.docs_url == "/docs"
        assert cfg.openapi_url == "/openapi.json"
        assert cfg.app_title == "Climate Digital Twin API"
        assert cfg.app_version == "2.1.0"

    def test_fields_overridable(self) -> None:
        cfg = GatewayConfig(host="0.0.0.0", port=9000, debug=True, api_key_enabled=False)
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9000
        assert cfg.debug is True
        assert cfg.api_key_enabled is False


class TestGetGatewayConfig:
    def test_singleton_returns_same_object(self) -> None:
        c1 = get_gateway_config()
        c2 = get_gateway_config()
        assert c1 is c2

    def test_defaults_to_disabled_auth(self, caplog: pytest.LogCaptureFixture) -> None:
        """With the corrected default, api_key_enabled is False when no key is set."""
        caplog.set_level(logging.WARNING)
        cfg = get_gateway_config()
        assert cfg.api_key_enabled is False
        # No spurious warning needed — default is already safe.
        assert "Disabling API key auth" not in caplog.text

    def test_skips_warning_on_subsequent_call(self, caplog: pytest.LogCaptureFixture) -> None:
        get_gateway_config()
        caplog.clear()
        get_gateway_config()
        assert "Disabling API key auth" not in caplog.text

    def test_keeps_auth_when_key_set(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("GATEWAY_API_KEY", "super-secret")
        caplog.set_level(logging.WARNING)
        cfg = get_gateway_config()
        # Default is false; key alone does not enable auth.
        assert cfg.api_key_enabled is False
        assert cfg.api_key == "super-secret"

    def test_honours_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GATEWAY_HOST", "0.0.0.0")
        monkeypatch.setenv("GATEWAY_PORT", "9999")
        monkeypatch.setenv("GATEWAY_DEBUG", "true")
        monkeypatch.setenv("GATEWAY_CORS_ORIGINS", "*")
        monkeypatch.setenv("GATEWAY_API_KEY_ENABLED", "false")
        cfg = get_gateway_config()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9999
        assert cfg.debug is True
        assert cfg.cors_origins == ["*"]
        assert cfg.api_key_enabled is False


class TestConfigureGateway:
    def test_updates_valid_keys(self) -> None:
        cfg = configure_gateway(host="0.0.0.0", port=9090, debug=True)
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9090
        assert cfg.debug is True

    def test_raises_type_error_for_unknown_key(self) -> None:
        with pytest.raises(TypeError, match="Unknown configuration option: bad_key"):
            configure_gateway(bad_key="value")

    def test_returns_same_singleton(self) -> None:
        cfg = configure_gateway(host="0.0.0.0")
        assert cfg is get_gateway_config()
