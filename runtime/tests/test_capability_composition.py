"""Tests for CapabilityRouter composition support."""

import pytest

from runtime.capabilities.base import CapabilityType
from runtime.capabilities.router import CapabilityRouter
from runtime.providers.registry import ProviderRegistry


@pytest.fixture
def router():
    r = CapabilityRouter()
    forecast = CapabilityType(
        name="forecast",
        description="Forecast capability",
        version="1.0",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        dependencies=[],
    )
    risk = CapabilityType(
        name="risk",
        description="Risk capability",
        version="1.0",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        dependencies=["forecast"],
    )
    report = CapabilityType(
        name="report",
        description="Report capability",
        version="1.0",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        dependencies=["forecast", "risk"],
    )
    r.register(forecast)
    r.register(risk)
    r.register(report)
    return r


class TestCapabilityComposition:
    def test_compose_no_deps(self, router):
        chain = router.compose("forecast")
        assert chain == ["forecast"]

    def test_compose_one_dep(self, router):
        chain = router.compose("risk")
        assert "forecast" in chain
        assert "risk" in chain
        # forecast should come before risk
        assert chain.index("forecast") < chain.index("risk")

    def test_compose_transitive(self, router):
        chain = router.compose("report")
        assert "forecast" in chain
        assert "risk" in chain
        assert "report" in chain
        # Order should be forecast -> risk -> report
        assert chain.index("forecast") < chain.index("risk") < chain.index("report")

    def test_compose_unknown(self, router):
        chain = router.compose("nonexistent")
        assert chain == ["nonexistent"]

    def test_compose_no_circular(self, router):  # noqa: ARG002
        """Circular dependencies should not cause infinite recursion."""
        r = CapabilityRouter()
        a = CapabilityType(
            name="a",
            description="",
            version="1",
            input_schema={},
            output_schema={},
            dependencies=["b"],
        )
        b = CapabilityType(
            name="b",
            description="",
            version="1",
            input_schema={},
            output_schema={},
            dependencies=["a"],
        )
        r.register(a)
        r.register(b)
        chain = r.compose("a")
        assert len(chain) <= 2  # Should not loop

    def test_resolve_chain(self, router):
        registry = ProviderRegistry()

        class MockProvider:
            provider_id = "mock"
            deterministic = True

            async def execute(self, _req):
                from runtime.models.provider import ProviderResult

                return ProviderResult(success=True, data={})

        registry.register("forecast", MockProvider())
        registry.register("risk", MockProvider())
        registry.register("report", MockProvider())
        chain = router.resolve_chain("report", registry)
        assert len(chain) == 3
        names = [c[0] for c in chain]
        assert names == ["forecast", "risk", "report"]
        # All should have providers
        for _, provider in chain:
            assert provider is not None
