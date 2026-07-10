# Climate Provider Adapters

Six provider adapters wrap legacy Copilot clients as Runtime Providers. Each adapter implements the `Provider` ABC from `runtime/providers/base.py` and handles a single climate capability.

## Architecture

```
Provider (ABC)
  ├── ForecastProviderAdapter → ForecastClient
  ├── RiskProviderAdapter → RiskClient
  ├── TwinStateProviderAdapter → TwinClient
  ├── ScenarioProviderAdapter → ScenarioClient
  ├── KnowledgeProviderAdapter → RAGClient
  └── ReportProviderAdapter → ReportClient
```

Each adapter:
1. Implements `async execute(request: ProviderRequest) -> ProviderResult`
2. Implements `health() -> ProviderHealth`
3. Declares `provider_id` and `capability` class attributes
4. Is stateless (can be shared across requests)

## ForecastProviderAdapter (`climate/providers/forecast.py`)

Wraps `ForecastClient` for temperature and rainfall predictions up to 7 days ahead.

- **Capability**: `forecast`
- **Input params**: `location` (required), `days` (default: 3)
- **Returns**: `{forecast: [{date, temperature, humidity, precipitation_probability}], location, days}`

```python
adapter = ForecastProviderAdapter()
result = await adapter.execute(ProviderRequest(
    capability="forecast",
    params={"location": "Bangalore", "days": 3},
    context=runtime_ctx,
))
# result.data = {"forecast": [...], "location": "Bangalore", "days": 3}
```

## RiskProviderAdapter (`climate/providers/risk.py`)

Wraps `RiskClient` for climate risk assessment scores.

- **Capability**: `risk`
- **Input params**: `location` (required), `use_model_shap` (default: True)
- **Returns**: `{risk_assessment: {heat_risk, flood_risk, drought_risk, composite_risk, category}, location}`

```python
adapter = RiskProviderAdapter()
result = await adapter.execute(ProviderRequest(
    capability="risk",
    params={"location": "Bangalore"},
    context=runtime_ctx,
))
# result.data["risk_assessment"] = {"heat_risk": 0.45, "flood_risk": 0.30, ...}
```

## TwinStateProviderAdapter (`climate/providers/twin_state.py`)

Wraps `TwinClient` for querying the current digital twin state.

- **Capability**: `twin_state`
- **Input params**: `location` (required)
- **Returns**: `{state: {temperature, humidity, rainfall, soil_moisture}, location}`

```python
adapter = TwinStateProviderAdapter()
result = await adapter.execute(ProviderRequest(
    capability="twin_state",
    params={"location": "Bangalore"},
    context=runtime_ctx,
))
# result.data["state"] = {"temperature": 28.5, "humidity": 65, ...}
```

## ScenarioProviderAdapter (`climate/providers/scenario.py`)

Wraps `ScenarioClient` for what-if climate scenario simulations.

- **Capability**: `scenario`
- **Input params**: `location`, `scenario_type` (temperature/rainfall/monsoon/extreme_event), `value` (default: 2.0)
- **Returns**: `{result: {...}, location, scenario_type}`

```python
adapter = ScenarioProviderAdapter()
result = await adapter.execute(ProviderRequest(
    capability="scenario",
    params={"location": "Bangalore", "scenario_type": "temperature", "value": 2.0},
    context=runtime_ctx,
))
```

## KnowledgeProviderAdapter (`climate/providers/knowledge.py`)

Wraps `RAGClient` for semantic knowledge base search.

- **Capability**: `knowledge`
- **Input params**: `query` (required), `top_k` (default: 3)
- **Returns**: `{results: [{title, snippet, score}], query, fallback}`

```python
adapter = KnowledgeProviderAdapter()
result = await adapter.execute(ProviderRequest(
    capability="knowledge",
    params={"query": "rainfall patterns in Karnataka", "top_k": 5},
    context=runtime_ctx,
))
```

## ReportProviderAdapter (`climate/providers/report.py`)

Wraps `ReportClient` for structured climate report generation.

- **Capability**: `report`
- **Input params**: `location`, `report_type` (summary/detailed/risk/forecast)
- **Returns**: `{report, location, report_type, findings, recommendations}`

## Testing

Each provider adapter has dedicated tests in `climate/tests/providers/`:

- `test_forecast.py`
- `test_risk.py`
- `test_twin_state.py`
- `test_scenario.py`
- `test_knowledge.py`
- `test_report.py`

All providers are deterministic (return mock data), which simplifies testing. The `deterministic` property returns `True` for all adapters.
