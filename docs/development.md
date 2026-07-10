# Development Guide

## Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install in editable mode
pip install -e ".[dev,ollama]"

# Verify installation
python -c "import runtime; import climate; print('OK')"
```

## Project Conventions

### Code Style

- Python 3.11+, type annotations required on all function signatures (92.9% coverage target)
- 100 character line limit (configured in `pyproject.toml`)
- Ruff for linting: `ruff check runtime/ climate/ copilot/`
- MyPy for type checking: `mypy runtime/ climate/ copilot/`
- No `eval()`, `exec()`, `pickle`, `subprocess`, or unsafe `yaml.load()` in production code
- No `TODO`, `FIXME`, or `HACK` comments in committed code

### Architecture Rules

Runtime code (`runtime/`) must never:
- Contain climate-specific terms (weather, rainfall, temperature, twin, forecast, etc.)
- Import from `climate` or `copilot` packages
- Reference domain-specific concepts

These rules are enforced by `runtime/test_architecture.py` using AST parsing and forbidden-term scanning.

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=runtime --cov=climate

# Run benchmarks
pytest runtime/benchmarks/ -v

# Run architecture tests
pytest runtime/test_architecture.py -v
```

- 461 tests total, all passing, 0 skipped
- test:code ratio: 0.44:1 (49 test files, 4,955 test lines)
- Benchmarks: 67 tests across 8 suites (WP1-WP8)

## How to Add a New Stage

1. Create a class inheriting from `PipelineStage` in `runtime/pipeline/stages/` (for domain-agnostic stages) or `climate/pipeline/stages/` (for domain-specific stages)

```python
from runtime.models.pipeline import PipelineStage, ExecutionContext

class MyStage(PipelineStage):
    name = "my_stage"
    description = "Does something useful"
    dependencies = ["previous_stage"]

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        # Read from blackboard
        data = ctx.blackboard.get("some.key")
        # Process
        result = process(data)
        # Write to blackboard
        ctx.blackboard.publish("my.key", result, self.name)
        ctx.stage_outputs["my_result"] = result
        return ctx
```

2. Register the stage in the pipeline definition inside `climate/plugin.py`:

```python
pipeline = CognitivePipeline(
    id="climate.interactive",
    triggers=["user_query"],
    stages=[
        IntentStage(),
        MyStage(),  # Add here
        # ... rest of stages
    ],
)
```

3. Write tests in the corresponding `tests/` directory
4. Run all tests to ensure no regressions

## How to Add a New Provider

1. Implement the `Provider` interface in `climate/providers/`:

```python
from runtime.providers.base import Provider
from runtime.models.provider import ProviderRequest, ProviderResult, ProviderHealth

class MyProvider(Provider):
    provider_id = "climate.my"
    capability = "my_capability"

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        # Implement
        pass

    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True)
```

2. Define the capability contract in `climate/capabilities/contracts.py`:

```python
MY_CAP = CapabilityType(
    name="my_capability",
    description="...",
    version="1.0.0",
    input_schema={...},
    output_schema={...},
    timeout_policy=TimeoutPolicy(default_ms=10000, max_ms=30000),
    dependencies=[],
)
ALL_CAPABILITIES.append(MY_CAP)
```

3. Register in `climate/plugin.py`:

```python
_PROVIDER_CONFIGS.append((
    "my_capability",
    MyProvider,
    MigrationEntry(...),
))
```

## How to Add a New Workflow

Define a `WorkflowDefinition` in `climate/workflows/`:

```python
from runtime.models.workflow import WorkflowDefinition, WorkflowStep

MY_WORKFLOW = WorkflowDefinition(
    id="my.workflow",
    name="My Workflow",
    triggers=["my_trigger"],
    steps=[
        WorkflowStep(id="step1", capability="forecast", params={}),
        WorkflowStep(id="step2", capability="risk", params={}, depends_on=["step1"]),
    ],
)
```

Register in `climate/plugin.py`: `engine.register(MY_WORKFLOW)`

## Benchmark Development

See `runtime/benchmarks/` for existing benchmark suites. Add new benchmarks following the pattern:

```python
from runtime.benchmarks import benchmark

class TestMyBenchmark:
    async def test_something(self):
        result = await benchmark("my_metric", my_function)
        assert result.p95 < 100  # 95th percentile under 100ms
```
