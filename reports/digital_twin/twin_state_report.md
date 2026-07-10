# Twin State Report

## Entity Model

### ClimateEntity (Dataclass)

```python
@dataclass
class ClimateEntity:
    location_id: str        # e.g., "KA-BLR-001"
    latitude: float         # Decimal degrees
    longitude: float        # Decimal degrees
    district: str           # District name
    timestamp: str          # ISO 8601
    rainfall: float         # mm
    max_temp: float         # Celsius
    min_temp: float         # Celsius
    risk_score: float       # 0–100
    prediction_confidence: float  # 0–1
    scenario_id: str        # Active scenario (if any)
    data_source: str        # "IMD", "INSAT", "forecast", "scenario", "risk_analysis"
    state_type: str         # "current", "forecast", "scenario", "rollback"
```

### Immutable Update Pattern

```python
entity = ClimateEntity(location_id="KA-BLR-001", ...)
modified = entity.update_state(
    rainfall=entity.rainfall + 10.0,
    max_temp=entity.max_temp + 2.0,
)
# original entity is unchanged
```

## State Manager

The `StateManager` (`simulator/state_manager/manager.py`) maintains an in-memory version chain per location. Each version is an immutable snapshot.

| Method | Description |
|--------|-------------|
| create_version(entity) | Appends new Version to chain |
| get_latest(location_id) | Returns most recent Version |
| rollback(location_id, version_id) | Creates new Version identical to target |
| get_all_location_ids() | Returns list of known locations |
| get_history(location_id) | Returns all versions for a location |

## Version Chain Example

For location `KA-BLR-001`:

| Version | State Type | Source | Timestamp |
|---------|-----------|--------|-----------|
| 1 | current | IMD | 2026-06-01T00:00:00 |
| 2 | forecast | forecast | 2026-06-02T00:00:00 |
| 3 | scenario | scenario(temp_plus_2) | 2026-06-02T00:05:00 |
| 4 | current | IMD | 2026-06-02T06:00:00 |

Rollback to v2 creates v5 identical to v2.

## State Response Schema

```json
{
  "location_id": "KA-BLR-001",
  "timestamp": "2026-06-29T12:00:00",
  "rainfall": 85.3,
  "max_temp": 32.1,
  "min_temp": 21.5,
  "risk_score": 45.0,
  "prediction_confidence": 0.87,
  "scenario_id": "",
  "data_source": "IMD",
  "state_type": "current"
}
```

## Location Naming Convention

`{State}-{District Abbreviation}-{3-digit index}`

| Location ID | District | Coordinates (lat, lon) |
|-------------|----------|----------------------|
| KA-BLR-001 | Bangalore | 12.97, 77.59 |
| KA-MYS-001 | Mysore | 12.30, 76.64 |
| KA-BEL-001 | Belgaum | 15.85, 74.50 |

## Storage

- Backend: Parquet files in `data/twin_store/`
- Compression: Snappy
- Each version stored as a row group
- Repository loads all versions on startup

## Default Fallback Values

When no real data is available for a location:

| Field | Default |
|-------|---------|
| rainfall | 50.0 mm |
| max_temp | 30.0°C |
| min_temp | 20.0°C |
| risk_score | 25.0 |
| prediction_confidence | 0.8 |
| data_source | "synthetic" |
| state_type | "current" |

## Validation Errors

| Error Message | Condition |
|---------------|-----------|
| "location_id is required" | Empty location_id |
| "Invalid latitude: {val}" | Outside [-90, 90] |
| "Invalid longitude: {val}" | Outside [-180, 180] |
| "Invalid rainfall: {val}" | Outside [0, 2000] |
| "Invalid max_temp: {val}" | Outside [-10, 55] |
| "Invalid min_temp: {val}" | Outside [-10, 55] |
| "Invalid state_type: {val}" | Not in StateType enum |
| "Latitude outside Karnataka bounds: {val}" | Outside [11.5, 18.5] |
| "Longitude outside Karnataka bounds: {val}" | Outside [74.0, 78.5] |
