
from runtime.capabilities.router import CapabilityRouter
from runtime.models.capability import CapabilityType
from runtime.providers.echo import EchoProvider
from runtime.providers.registry import ProviderRegistry


class TestCapabilityRouter:
    def test_register_and_resolve(self):
        router = CapabilityRouter()
        ct = CapabilityType(
            name="test.cap",
            description="Test",
            version="1.0",
            input_schema={},
            output_schema={},
        )
        router.register(ct)
        resolved = router.resolve("test.cap")
        assert resolved is not None
        assert resolved.name == "test.cap"

    def test_resolve_nonexistent(self):
        router = CapabilityRouter()
        assert router.resolve("nonexistent") is None

    def test_select_provider(self):
        router = CapabilityRouter()
        registry = ProviderRegistry()
        registry.register("runtime.echo", EchoProvider())
        ct = CapabilityType(
            name="runtime.echo",
            description="",
            version="1",
            input_schema={},
            output_schema={},
        )
        router.register(ct)
        provider = router.select_provider("runtime.echo", registry)
        assert provider is not None
        assert provider.provider_id == "runtime.echo"

    def test_select_provider_no_match(self):
        router = CapabilityRouter()
        registry = ProviderRegistry()
        assert router.select_provider("nonexistent", registry) is None

    def test_validate_contract_no_capability(self):
        router = CapabilityRouter()
        assert router.validate_contract("nonexistent", {}, {}) is False

    def test_list_capabilities(self):
        router = CapabilityRouter()
        ct1 = CapabilityType(
            name="cap1", description="", version="1", input_schema={}, output_schema={}
        )
        ct2 = CapabilityType(
            name="cap2", description="", version="2", input_schema={}, output_schema={}
        )
        router.register(ct1)
        router.register(ct2)
        caps = router.list_capabilities()
        assert "cap1" in caps
        assert "cap2" in caps
