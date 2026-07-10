# Configuration Guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FORECAST_SERVICE_URL` | `http://forecast-engine:8006` | URL for forecast service (used by copilot_forecast_client.py) |
| `RISK_SERVICE_URL` | `http://risk-engine:8003` | URL for risk service (used by copilot_risk_client.py) |
| `COPILOT_API_URL` | dashboard config | URL for copilot API (used by 07_copilot_chat.py) |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering (Docker) |
| `BENCHMARK_ITERATIONS` | `100` | Number of iterations for benchmark tests |

## Runtime Configuration

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

All caches support:
- `max_size`: maximum entries before LRU-like eviction
- `default_ttl`: default TTL in seconds (per-cache override)
- Per-entry TTL override when calling `set()`

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

### Memory (`runtime/models/memory.py`)

| Store | Default | Description |
|-------|---------|-------------|
| ConversationMemory | max_turns=50 | Maximum conversation turns retained |
| ToolOutputCache | default_ttl=300s | Default TTL for cached tool outputs |

### Pipeline Stages

| Stage | Configurable Parameter | Default |
|-------|----------------------|---------|
| RetrievalStage | `default_top_k` | 5 |
| RetrievalStage | `min_score` | 0.3 |
| GroundingStage | `min_confidence` | 0.3 |
| ReasoningStage | `prefer_deterministic` | True |
| EvidenceAggregationStage | `dependency_map` | {} (injected by ClimatePlugin) |
| ExecutionStage | (uses stage timeout) | 30,000ms |
| IntentStage | pattern-based | (not configurable) |

### Pipeline Engine

| Parameter | Default | Description |
|-----------|---------|-------------|
| Stage `timeout_ms` | 30,000ms | Per-stage execution timeout |
| Pipeline `timeout_ms` | 60,000ms | Pipeline-wide timeout |
| ExecutionContext MAX_TRACE_ENTRIES | 500 | Max trace entries per execution |
| RuntimeContext MAX_TRACE_LOG | 1,000 | Max trace log entries per request |

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

## Docker Configuration

See `docker-compose.benchmark.yml`:

```yaml
services:
  runtime-benchmark:
    build:
      context: .
      dockerfile: Dockerfile.benchmark
    volumes:
      - ./reports:/reports
    environment:
      - PYTHONUNBUFFERED=1
      - BENCHMARK_ITERATIONS=100
```

## pyproject.toml

Dependencies are declared in `pyproject.toml` with version pins:

- **Runtime**: aiohttp, requests, pyyaml, python-dateutil, pydantic
- **Dev**: pytest, pytest-asyncio, pytest-cov, coverage, ruff, mypy, pre-commit
- **Ollama**: ollama, httpx
