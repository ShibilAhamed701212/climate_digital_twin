# Digital Twin Report

## Overview
The Digital Twin is a stateful, versioned representation of Karnataka's climate system. It ingests observations from authoritative sources (IMD, INSAT-3D), applies forecast predictions, runs what-if scenarios, and tracks risk scores — all with full version history and rollback capability.

## Architecture

### Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| DigitalTwinEngine | `simulator/engine/twin_engine.py` | Central orchestrator — wires StateManager, Repository, EventBus, TwinService |
| TwinService | `simulator/services/twin_service.py` | Business logic layer — validation, state transitions, event publishing |
| StateManager | `simulator/state_manager/manager.py` | Immutable version chain per location |
| ParquetRepository | `simulator/repository/parquet_repository.py` | Persistent storage (Snappy-compressed Parquet) |
| EventBus | `simulator/events/event_bus.py` | Pub-sub for state change notifications |
| ClimateEntity | `simulator/entities/climate_entity.py` | Domain model — 13 attributes, immutable update pattern |

### State Types

| StateType | Value | Description |
|-----------|-------|-------------|
| CURRENT | `current` | Latest observation from authoritative source |
| FORECAST | `forecast` | ML model prediction output |
| SCENARIO | `scenario` | What-if simulation state |
| ROLLBACK | `rollback` | Restored previous state |

### API Endpoints (Twin State Manager:8001)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/state/current` | Current state for a location |
| GET | `/state/history` | Historical states for a location |
| GET | `/state/version-history` | Version history for a location |
| POST | `/state/sync` | Ingest a new observation |
| GET | `/forecast/state` | Get forecast state for a location |
| POST | `/scenarios/simulate` | Apply a what-if scenario |
| POST | `/rollback` | Rollback to a specific version |

### Configuration

Defined in `simulator/configs/twin_config.yaml`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| twin.name | karnataka_climate_twin | Twin identifier |
| twin.version | 1.0.0 | Schema version |
| twin.region | Karnataka | Geographic scope |
| twin.grid_resolution | 0.25 | Grid cell size in degrees |
| storage.engine | duckdb | Storage backend |
| storage.path | data/twin_store | Data directory |
| storage.parquet_compression | snappy | Compression codec |
| state.max_versions_per_entity | 1000 | Version limit per location |
| state.enforce_immutable | true | No in-place updates |
| state.validate_coordinates | true | Karnataka bounds check |
| state.validate_temperatures.min/max | -10 / 55 | Valid temperature range |
| state.validate_rainfall.min/max | 0 / 2000 | Valid rainfall range (mm) |
| events.enabled | true | Event bus active |
| events.max_subscribers | 50 | Max event bus subscribers |
| api.host | 0.0.0.0 | API bind address |
| api.port | 8001 | API port |

## Data Flow

```
IMD/INSAT → /state/sync → TwinService → StateManager → ParquetRepository
                                              ↓
                                         EventBus → Subscribers
                                              ↓
                                    /state/current (read)
                                              ↓
Forecast Engine → /forecast/state → TwinService → StateManager
                                              ↓
Scenario Engine → /scenarios/simulate → TwinService → StateManager
                                              ↓
Risk Engine → update_risk_score → TwinService → StateManager
```

## Versioning

Each state mutation creates an immutable version:

```
Version {
  version_id: int (auto-incrementing)
  location_id: str
  timestamp: str (ISO 8601)
  state_type: str (current|forecast|scenario|rollback)
  entity_data: dict (serialized ClimateEntity)
}
```

- Max 1,000 versions per entity
- Rollback creates a new version (not destructive)
- Versions persisted as Parquet in `data/twin_store/`

## Validation Rules

| Rule | Parameter | Constraint |
|------|-----------|------------|
| Coordinates | latitude | 11.5–18.5 (Karnataka bounds) |
| Coordinates | longitude | 74.0–78.5 (Karnataka bounds) |
| Temperature | max_temp | -10 to 55°C |
| Temperature | min_temp | -10 to 55°C |
| Rainfall | rainfall | 0–2000 mm |
| State Type | state_type | Must be valid StateType enum |

## Events

| Event Type | Trigger | Data |
|------------|---------|------|
| ObservationUpdated | /state/sync | version_id, state_type |
| ForecastGenerated | /forecast/state | version_id, confidence |
| ScenarioApplied | /scenarios/simulate | version_id, scenario_id |
| RiskUpdated | update_risk_score | version_id, risk_score |
| TwinRefreshed | refresh_twin | locations list |

## Performance

- State sync: <10ms per observation (cold Parquet write)
- Version retrieval: <2ms per version (indexed)
- Rollback: <5ms (creates new version)
- Maximum concurrent locations: Limited by Parquet I/O

## Known Limitations

1. ParquetRepository uses filesystem-based storage — not distributed
2. No built-in authentication on state endpoints
3. Grid resolution fixed at 0.25° (configurable but requires re-indexing)
4. No automatic purging of old versions (manual cleanup needed)
