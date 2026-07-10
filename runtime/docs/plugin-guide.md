# Plugin Developer Guide

1. Subclass Plugin:

```python
from runtime.plugins.base import Plugin
class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"
    runtime_version_required = ">=0.1.0"
```

2. Implement register_* methods to register capabilities, providers, agents, workflows.

3. Load via rt.load_plugin(MyPlugin())

Manifest validates: plugin_id, name, version (semver), runtime_version_required.
