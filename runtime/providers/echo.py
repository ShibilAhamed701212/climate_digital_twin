from runtime.models.provider import ProviderHealth, ProviderRequest, ProviderResult
from runtime.providers.base import Provider


class EchoProvider(Provider):
    """Built-in test provider. Returns whatever params it receives."""

    provider_id = "runtime.echo"
    capability = "runtime.echo"

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(success=True, data=request.params, confidence=1.0)

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, version="0.1.0")
