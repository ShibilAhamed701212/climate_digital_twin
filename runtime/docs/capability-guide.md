# Capability Guide

Capabilities are contracts defined by:
- input_schema (JSON Schema)
- output_schema (JSON Schema)
- error_schema (JSON Schema)
- timeout_policy, retry_policy, cache_policy
- required_permissions

Register: `router.register(capability_type)`
Resolve: `router.resolve("capability_name")`
Validate: `router.validate_contract("cap_name", input_data, output_data)`
