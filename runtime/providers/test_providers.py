import pytest

from runtime.models.provider import ProviderRequest
from runtime.models.runtime import RuntimeContext
from runtime.providers.base import Provider
from runtime.providers.echo import EchoProvider
from runtime.providers.registry import ProviderRegistry


class TestProviderBase:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            Provider()

    def test_echo_provider_attributes(self):
        p = EchoProvider()
        assert p.provider_id == "runtime.echo"
        assert p.capability == "runtime.echo"
        assert p.deterministic is True


class TestEchoProvider:
    @pytest.mark.asyncio
    async def test_execute(self):
        p = EchoProvider()
        ctx = RuntimeContext(trace_id="t1")
        req = ProviderRequest(
            capability="runtime.echo", params={"msg": "hello"}, context=ctx
        )
        result = await p.execute(req)
        assert result.success is True
        assert result.data["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_health(self):
        p = EchoProvider()
        h = p.health()
        assert h.ok is True


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        p = EchoProvider()
        registry.register("runtime.echo", p)
        providers = registry.all_for("runtime.echo")
        assert len(providers) == 1
        assert providers[0].provider_id == "runtime.echo"

    def test_get_best_deterministic(self):
        registry = ProviderRegistry()
        registry.register("runtime.echo", EchoProvider())
        best = registry.get_best("runtime.echo", {"allow_deterministic": True})
        assert best is not None
        assert best.provider_id == "runtime.echo"

    def test_get_best_empty(self):
        registry = ProviderRegistry()
        assert registry.get_best("nonexistent", {}) is None

    def test_all_for_empty(self):
        registry = ProviderRegistry()
        assert registry.all_for("nonexistent") == []

    def test_multiple_providers_same_capability(self):
        registry = ProviderRegistry()
        registry.register("echo", EchoProvider())
        registry.register("echo", EchoProvider())
        assert len(registry.all_for("echo")) == 2
