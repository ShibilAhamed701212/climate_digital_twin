# Climate Provider Adapters

> **Note:** Provider adapters are in the `climatedt/` package. They implement the `Provider` interface from the AI Runtime (`runtime/providers/base.py`).

## Overview

Six provider adapters wrap backend microservice clients as Runtime Providers. Each adapter handles a single climate capability.

### Architecture

```
Provider (runtime/providers/base.py)
  ├── ForecastProviderAdapter → calls forecast-engine:8006
  ├── RiskProviderAdapter → calls risk-engine:8003
  ├── TwinStateProviderAdapter → calls twin-state-mgr:8001
  ├── ScenarioProviderAdapter → calls scenario-engine:8002
  ├── KnowledgeProviderAdapter → calls rag-service:8004
  └── ReportProviderAdapter → calls report-service:8007
```

Each adapter:
1. Implements `async execute(request: ProviderRequest) -> ProviderResult`
2. Implements `health() -> ProviderHealth`
3. Declares `provider_id` and `capability` class attributes
4. Is stateless (can be shared across requests)

## Data Status

**All providers return synthetic data by default.** The dashboard API client (`dashboard/services/api_client.py`) has automatic synthetic fallback when services are unreachable.

## Provider Details

### ForecastProviderAdapter
- **Capability**: `forecast`
- **Input params**: `location` (required), `days` (default: 3)
- **Backend**: forecast-engine:8006
- **Returns**: `{forecast: [{date, temperature, humidity, precipitation_probability}], location, days}`

### RiskProviderAdapter
- **Capability**: `risk`
- **Input params**: `location` (required), `use_model_shap` (default: True)
- **Backend**: risk-engine:8003
- **Returns**: `{risk_assessment: {heat_risk, flood_risk, drought_risk, composite_risk, category}, location}`

### TwinStateProviderAdapter
- **Capability**: `twin_state`
- **Input params**: `location` (required)
- **Backend**: twin-state-mgr:8001
- **Returns**: `{state: {temperature, humidity, rainfall, soil_moisture}, location}`

### ScenarioProviderAdapter
- **Capability**: `scenario`
- **Input params**: `location`, `scenario_type` (temperature/rainfall/monsoon/extreme_event), `value`
- **Backend**: scenario-engine:8002
- **Returns**: `{result: {...}, location, scenario_type}`

### KnowledgeProviderAdapter
- **Capability**: `knowledge`
- **Input params**: `query` (required), `top_k` (default: 3)
- **Backend**: rag-service:8004
- **Returns**: `{results: [{title, snippet, score}], query, fallback}`
- **Note**: FAISS index is **empty by default** — must re-run indexing

### ReportProviderAdapter
- **Capability**: `report`
- **Input params**: `location`, `report_type` (summary/detailed/risk/forecast)
- **Backend**: report-service:8007
- **Returns**: `{report, location, report_type, findings, recommendations}`

## Testing

Tests exist in `tests/` directory covering the dashboard API client with synthetic fallback behavior.
