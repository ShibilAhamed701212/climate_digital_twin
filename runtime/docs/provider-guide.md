# Provider Guide

Implement Provider ABC:
- execute(request) -> ProviderResult
- health() -> ProviderHealth
- deterministic property

Register: `registry.register("capability_name", provider_instance)`
Select: `registry.get_best("capability_name", constraints)`
