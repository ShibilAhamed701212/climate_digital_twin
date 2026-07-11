# Runtime, Climate Domain, and Copilot Integration

## Overview

The system integrates three layers with strict dependency direction: Domain code → Runtime. Never the reverse.

```
Dashboard (Streamlit, page_views/)
    │
    ▼
API Client (dashboard/services/api_client.py)
    │
    ├──► Backend Services (Docker)
    │       api-gateway, twin-state-mgr, forecast-engine,
    │       scenario-engine, risk-engine, copilot-agent, etc.
    │
    └──► Synthetic Data Fallback (when services unavailable)
```

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Dashboard Layer                         │
│  dashboard/app.py · page_views/ · sidebar_nav.py        │
│  services/api_client.py · components/ · charts/          │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────┐
│                   Service Layer                           │
│  api-gateway :8000  ·  twin-state-mgr :8001             │
│  forecast-engine :8006  ·  risk-engine :8003            │
│  scenario-engine :8002  ·  copilot-agent :8005          │
│  rag-service :8004  ·  report-service :8007             │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Domain Logic Layer                      │
│  climatedt/ (climate-specific)                          │
│  models/ (ML definitions)                               │
│  knowledge/ (RAG pipeline)                              │
│  risk/ (risk engine)                                    │
│  simulator/ (scenario simulation)                       │
│  pipeline/ (data pipelines)                             │
└──────────────────────────┬──────────────────────────────┘
                           │ Plugin Interface
┌──────────────────────────▼──────────────────────────────┐
│                   AI Runtime Layer                        │
│  runtime/ (domain-agnostic)                             │
│  PipelineEngine · Blackboard · EventBus                 │
│  ProviderRegistry · PluginLoader · WorkflowEngine        │
└─────────────────────────────────────────────────────────┘
```

## Dependency Direction

```
climatedt/  →  runtime/  (domain code uses runtime interfaces)
copilot/    →  runtime/  (agent code uses runtime interfaces)
dashboard/  →  services/ (HTTP calls to backend)
services/   →  runtime/  (optional runtime integration)
```

The Runtime has zero knowledge of climate concepts. Domain isolation is enforced by architecture tests in `runtime/test_architecture.py`.

## Startup Sequence

1. **Docker compose up** starts all services
2. **API Gateway** initializes FastAPI with routers
3. **Backend services** register with health checks
4. **Dashboard** starts Streamlit app, connects to API Gateway
5. If services unavailable, **synthetic data fallback** kicks in

## Data Flow (Synthetic)

```
Dashboard (user interaction)
    → API Client (DashboardAPIClient)
    → Tries to call backend service
    → Service unavailable → SYNTHETIC DATA FALLBACK
    → Dashboard renders with generated data
```

## Testing Integration

- **2,266 tests** total
- Dashboard tests: 109 tests, all passing
- Tests use `DashboardAPIClient` with synthetic data
- No real service dependencies required for testing
