# Configuration Guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TWIN_STATE_MGR_PORT` | `8001` | Port for twin state manager |
| `FORECAST_PORT` | `8006` | Port for forecast engine |
| `SCENARIO_PORT` | `8002` | Port for scenario engine |
| `RISK_PORT` | `8003` | Port for risk engine |
| `COPILOT_PORT` | `8005` | Port for copilot agent |
| `RAG_PORT` | `8004` | Port for RAG service |
| `REPORT_PORT` | `8007` | Port for report service |
| `API_PORT` | `8000` | Port for API gateway |
| `DASHBOARD_PORT` | `8051` | Port for dashboard (Docker) |
| `CLIMATEDT_DATA_DIR` | `/app/data` | Data directory for climate DT |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |

## Runtime Configuration (`runtime/`)

### Blackboard (`runtime/blackboard.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_VERSIONS_PER_KEY` | `100` | Maximum versions retained per blackboard key |
| TTL per entry | None (optional) | Time-to-live in seconds per key-value entry |

### EventBus (`runtime/event_bus.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_HISTORY` | `10,000` | Maximum events retained in history deque |

### Cache (`runtime/cache/`)

| Cache | Default TTL | Default Max Size | Description |
|-------|-------------|------------------|-------------|
| ProviderCache | 60s | 1,000 | Caches provider results by capability + params hash |
| RetrievalCache | 300s | 500 | Caches retrieval results by normalized query |
| ReasoningCache | 600s | 200 | Caches reasoning outputs by evidence hash |
| ResolutionCache (compose) | 86,400s (24h) | 100 | Caches capability dependency chains |
| ResolutionCache (resolve) | 86,400s (24h) | 100 | Caches provider resolution chains |

### Circuit Breaker (`runtime/reliability.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Consecutive failures before circuit opens |
| `recovery_timeout` | 30.0s | Seconds before OPEN → HALF_OPEN transition |
| `half_open_max_calls` | 1 | Probe calls allowed in HALF_OPEN state |

### Retry (`runtime/reliability.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_attempts` | 3 | Maximum retry attempts (including first) |
| `base_delay` | 0.5s | Initial backoff delay |
| `max_delay` | 30.0s | Maximum backoff cap |
| `backoff_factor` | 2.0 | Exponential multiplier per attempt |

### Performance Budgets (`runtime/performance_budget.py`)

| Operation | Budget | Description |
|-----------|--------|-------------|
| blackboard.publish | 1ms | Publish should complete in under 1ms |
| blackboard.get | 0.5ms | Read should complete in under 0.5ms |
| event_bus.publish | 1ms | Event publish should complete in under 1ms |
| provider_registry.register | 1ms | Register should complete in under 1ms |
| plugin.load | 50ms | Load minimal plugin in under 50ms |
| runtime.initialize | 100ms | Runtime init in under 100ms |
| runtime.shutdown | 100ms | Runtime shutdown in under 100ms |

## Dashboard Configuration (`dashboard/config/`)

### Sample Locations
15 hardcoded Karnataka districts (defined in `dashboard/config/config.py`):
- Bengaluru Urban, Bengaluru Rural, Mysuru, Mangaluru, etc.

### Synthetic Data Fallback
The API client (`dashboard/services/api_client.py`) automatically falls back to synthetic data when microservices are unavailable. This is the default behavior — all data in the dashboard is synthetic unless services are running with real data.

## Data Configuration (`config/data_config.yaml`)

YAML-based configuration for data sources, pipelines, and storage settings. Supports both real (NASA POWER, Open-Meteo) and synthetic data source configuration.

## Docker Configuration

See `docker-compose.yml` for all service configurations including:
- Port mappings
- Volume mounts (twin_data, model_data)
- Resource limits (memory, CPU)
- Health check intervals
- Network configuration

## pyproject.toml

Dependencies declared in `pyproject.toml`:

- **Core**: fastapi, uvicorn, httpx, requests, aiohttp
- **Data**: pandas, numpy, scipy, pyarrow, pyyaml
- **ML**: torch, scikit-learn, xgboost, prophet, statsmodels, shap
- **RAG**: faiss-cpu, sentence-transformers
- **Dashboard**: streamlit, plotly, folium, streamlit-folium, geopandas
- **Dev**: pytest, pytest-cov, coverage, ruff, black, mypy, pre-commit, bandit, pip-audit
