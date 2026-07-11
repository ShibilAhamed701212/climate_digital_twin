# Copilot Client Adapters

## Overview

The `copilot/clients/` package contains client classes that provide **mock data** to the dashboard. These are functional stubs — no real backend service integration.

## Client List

| Client | File | Purpose | Status |
|--------|------|---------|--------|
| ForecastClient | `forecast_client.py` | Forecast predictions | **Mock data** |
| RiskClient | `risk_client.py` | Risk assessment | **Mock data** |
| TwinClient | `twin_client.py` | Twin state | **Mock data** |
| RAGClient | `rag_client.py` | Knowledge search | **Mock data** |
| ReportClient | `report_client.py` | Report generation | **Mock data** |

## Example Usage

```python
from copilot.clients.forecast_client import ForecastClient

client = ForecastClient(base_url="http://forecast-engine:8006")
predictions = client.predict(location="Bengaluru Urban", days=3)
# Returns mock data:
# [{"date": "2025-06-15", "temperature": 28.5, "humidity": 65, ...}, ...]
```

## Data Patterns

All clients return deterministic mock data:
- **ForecastClient**: temperature increments by 0.5°C/day, humidity decreases by 2%/day
- **RiskClient**: returns fixed risk scores with minor per-location variation
- **TwinClient**: returns hardcoded state values per location
- **RAGClient**: returns templated search results with decreasing scores
- **ReportClient**: returns structured report with generic findings

## Dashboard Integration

The dashboard (`dashboard/services/api_client.py`) uses its own API client class that calls backend services and falls back to synthetic data generation when services are unavailable. The `DashboardAPIClient` is the primary interface used by dashboard pages, not the Copilot client classes directly.

## Status

These clients are functional stubs for the hackathon. They provide mock data that allows the dashboard and pipeline stages to render and test correctly. No real data integration exists.
